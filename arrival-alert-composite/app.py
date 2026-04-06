import os
import httpx
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor
from flasgger import Swagger
import requests

load_dotenv()
app = Flask(__name__)

# --- Swagger Setup ---
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True, 
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}

template = {
    "swagger": "2.0",
    "info": {
        "title": "Gantry Arrival Service API",
        "description": "Handles vehicle arrivals, order status updates, and background notifications.",
        "version": "1.0.0"
    }
}

swagger = Swagger(app, config=swagger_config, template=template)
# ---------------------

# Increased workers to handle background updates and emails simultaneously
executor = ThreadPoolExecutor(max_workers=20)

# API links
ORDER_API = os.environ.get("ORDER_API")
MERCHANT_API = os.environ.get("MERCHANT_API")
CUSTOMER_API = os.environ.get("CUSTOMER_API")
GANTRY_API = os.environ.get("GANTRY_API")
PUBLISHER_API = os.environ.get("PUBLISHER_API")

# Global client saves ~500ms by reusing TCP connections
limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
client = httpx.Client(limits=limits, timeout=10.0)

def background_processing(email, subject, message, order_id=None, merchant_id=None, status=None, notification_type="general"):
    """Handles slow IO (Emails and DB Updates) without blocking the Gantry."""
    # 1. Send the Notification
    try:
        requests.post(PUBLISHER_API, json={
            "email": email, "subject": subject, "message": message, "notification_type": notification_type
        }, timeout=5)
    except Exception as e:
        print(f"Notification error: {e}")

    # 2. Update Order Status in DB (If applicable)
    if order_id and status:
        try:
            requests.put(f"{ORDER_API}/order", json={
                "order_id": order_id, "order_status": status, "merchant_id": merchant_id
            }, timeout=5)
        except Exception as e:
            print(f"DB Update error: {e}")

@app.route('/arrival', methods=['POST'])
def handle_arrival():
    """
    Handle Vehicle Arrival at Gantry
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - license_plate
          properties:
            license_plate:
              type: string
              example: "SMS1111R"
              description: The license plate of the arriving vehicle.
    responses:
      200:
        description: Arrival processed (Order found and Gantry notified)
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            message:
              type: string
              example: "Arrival recorded for SMS1111R"
      400:
        description: Bad Request - Missing license_plate
      404:
        description: Not Found - No orders found for this plate today
    """

    data = request.get_json()
    if not data or 'license_plate' not in data:
        return jsonify({"error": "Missing license_plate"}), 400

    license_plate = data['license_plate']
    
    # 1. Fetch Orders (Critical Path)
    order_res = client.get(f"{ORDER_API}/order/plate?plate_num={license_plate}&date={date.today()}")
    if order_res.status_code != 200 or "data" not in order_res.json():
        return jsonify({"status": 404, "errorMsg": "No orders found"}), 404
    
    orders = order_res.json()["data"]
    master_status = 3 # Default to ARRIVED OUTSIDE OPERATIONAL HOURS
    first_order = orders[0]
    final_customer_name = "Customer"

    # 2. Prepare ALL metadata requests to run in parallel
    # Fetch customer once (all orders have same customer)
    customer_id = orders[0]['customer_id']
    customer_res = client.get(f"{CUSTOMER_API}/customer/{customer_id}")
    # Fetch merchants for each order
    merchant_responses = []
    for order in orders:
        merchant_responses.append(client.get(f"{MERCHANT_API}/merchant/{order['sc_id']}/{order['merchant_id']}"))
    # 3. Process Logic with your original message templates
    c_data = customer_res.json()["data"]  # Customer data (same for all orders)
    for i, merchant_res in enumerate(merchant_responses):
        m_data = merchant_res.json()["data"]
        order = orders[i]  # Corresponding order
        
        final_customer_name = c_data['customer_name']
        time_now = datetime.now().time()
        opening = datetime.strptime(m_data["opening_time"], "%H:%M:%S").time()
        closing = datetime.strptime(m_data["closing_time"], "%H:%M:%S").time()

        if time_now > closing:
            # STATUS 3: CLOSED
            msg = f"Hi {c_data['customer_name']},<br/><br/>We have closed for today, please come back when we open to retry your item pickup <br/><br/>- {m_data['merchant_name']}"
            executor.submit(background_processing, c_data['email'], f"{m_data['merchant_name']} - We missed you today, {c_data['customer_name']}.", msg, 
                            order['order_id'], order['merchant_id'], 3, notification_type="customer")
            
        elif time_now < opening:
            # TOO EARLY
            msg = f"Hi {c_data['customer_name']},<br/><br/>We noticed you came before we open and we are still busy setting up! Please come back later today when we open from {m_data['opening_time'][:5]} to {m_data['closing_time'][:5]} <br/><br/>- {m_data['merchant_name']}"
            executor.submit(background_processing, c_data['email'], f"{m_data['merchant_name']} - We haven't finished setting up!", msg, notification_type="customer")
            
        else:
            # STATUS 2: SUCCESSFUL ARRIVAL
            master_status = 2
            staff_msg = f"Hi Staff, <br/<br/>Customer {c_data['customer_name']} has arrived to pickup order {order['order_id']}, please prepare to deliver the order to the loading bay slot."
            executor.submit(background_processing, m_data['email'], f"[ORDER] Customer {c_data['customer_name']} has arrived to pickup order {order['order_id']}", staff_msg, 
                            order['order_id'], order['merchant_id'], 2, notification_type="customer")

    # 4. Single Gantry Call (Critical Path)
    gantry_payload = {
        "OrderId": first_order['order_id'],
        "CustomerId": first_order['customer_id'],
        "sc_id": first_order['sc_id'],
        "OrderStatus": master_status,
        "RequestedBy": final_customer_name
    }
    
    gantry_res = client.post(f"{GANTRY_API}/{license_plate}", json=gantry_payload)
    
    # Check for Gantry Availability
    if gantry_res.status_code == 200 and gantry_res.json().get('AccessStatus') == 'WAITING':
        wait_msg = f"Dear {final_customer_name}, <br/><br/>Please be informed that we currently have no available loading slots, please wait or come back in a few minutes"
        executor.submit(background_processing, first_order.get('email'), "No Slots Available now", wait_msg, notification_type="gantry")

    return jsonify({"status": 200, "message": f"Arrival recorded for {license_plate}"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)