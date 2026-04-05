import os
import asyncio
import httpx
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
app = Flask(__name__)
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
async_client = httpx.AsyncClient(limits=limits, timeout=10.0)

def background_processing(email, subject, message, order_id=None, merchant_id=None, status=None):
    """Handles slow IO (Emails and DB Updates) without blocking the Gantry."""
    import requests
    # 1. Send the Notification
    try:
        requests.post(PUBLISHER_API, json={
            "email": email, "subject": subject, "message": message, "notification_type": "info"
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
async def handle_arrival():
    data = request.get_json()
    if not data or 'license_plate' not in data:
        return jsonify({"error": "Missing license_plate"}), 400

    license_plate = data['license_plate']
    
    # 1. Fetch Orders (Critical Path)
    order_res = await async_client.get(f"{ORDER_API}/order/plate?plate_num={license_plate}&date={date.today()}")
    if order_res.status_code != 200 or "data" not in order_res.json():
        return jsonify({"status": 404, "errorMsg": "No orders found"}), 404
    
    orders = order_res.json()["data"]
    master_status = 3 # Default to ARRIVED OUTSIDE OPERATIONAL HOURS
    first_order = orders[0]
    final_customer_name = "Customer"

    # 2. Prepare ALL metadata requests to run in parallel
    metadata_tasks = []
    for order in orders:
        metadata_tasks.append(async_client.get(f"{CUSTOMER_API}/customer/{order['customer_id']}"))
        metadata_tasks.append(async_client.get(f"{MERCHANT_API}/merchant/{order['sc_id']}/{order['merchant_id']}"))
    
    # Wait for ALL customers and merchants at once (Collapses time significantly)
    meta_responses = await asyncio.gather(*metadata_tasks)

    # 3. Process Logic with your original message templates
    for i in range(0, len(meta_responses), 2):
        c_data = meta_responses[i].json()["data"]
        m_data = meta_responses[i+1].json()["data"]
        order = orders[i // 2]
        
        final_customer_name = c_data['customer_name']
        time_now = datetime.now().time()
        opening = datetime.strptime(m_data["opening_time"], "%H:%M:%S").time()
        closing = datetime.strptime(m_data["closing_time"], "%H:%M:%S").time()

        if time_now > closing:
            # STATUS 3: CLOSED
            msg = f"Hi {c_data['customer_name']},<br/><br/>We have closed for today, please come back when we open to retry your item pickup <br/><br/>- {m_data['merchant_name']}"
            executor.submit(background_processing, c_data['email'], f"{m_data['merchant_name']} - We missed you today, {c_data['customer_name']}.", msg, 
                            order['order_id'], order['merchant_id'], 3)
            
        elif time_now < opening:
            # TOO EARLY
            msg = f"Hi {c_data['customer_name']},<br/><br/>We noticed you came before we open and we are still busy setting up! Please come back later today when we open from {m_data['opening_time'][:5]} to {m_data['closing_time'][:5]} <br/><br/>- {m_data['merchant_name']}"
            executor.submit(background_processing, c_data['email'], f"{m_data['merchant_name']} - We haven't finished setting up!", msg)
            
        else:
            # STATUS 2: SUCCESSFUL ARRIVAL
            master_status = 2
            staff_msg = f"Hi Staff, <br/<br/>Customer {c_data['customer_name']} has arrived to pickup order {order['order_id']}, please prepare to deliver the order to the loading bay slot."
            executor.submit(background_processing, m_data['email'], f"[ORDER] Customer {c_data['customer_name']} has arrived to pickup order {order['order_id']}", staff_msg, 
                            order['order_id'], order['merchant_id'], 2)

    # 4. Single Gantry Call (Critical Path)
    gantry_payload = {
        "OrderId": first_order['order_id'],
        "CustomerId": first_order['customer_id'],
        "sc_id": first_order['sc_id'],
        "OrderStatus": master_status,
        "RequestedBy": final_customer_name
    }
    
    gantry_res = await async_client.post(f"{GANTRY_API}/{license_plate}", json=gantry_payload)
    
    # Check for Gantry Availability
    if gantry_res.status_code == 200 and gantry_res.json().get('AccessStatus') == 'WAITING':
        wait_msg = f"Dear {final_customer_name}, <br/><br/>Please be informed that we currently have no available loading slots, please wait or come back in a few minutes"
        executor.submit(background_processing, first_order.get('email'), "No Slots Available now", wait_msg)

    return jsonify({"status": 200, "message": f"Arrival recorded for {license_plate}"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)