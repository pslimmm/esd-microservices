from flask import Flask, jsonify, request
from datetime import datetime, timezone
import requests
import os
from dotenv import load_dotenv
from flasgger import Swagger

app = Flask(__name__)

# --- Swagger Config ---
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
        "title": "Merchant Management API",
        "description": "Service to manage active pickups and order status updates.",
        "version": "1.0.0"
    }
}

swagger = Swagger(app, config=swagger_config, template=template)
# ----------------------

load_dotenv()

# -----------------------------------------------
# Configuration
# -----------------------------------------------
ORDER_API_URL = os.environ.get("ORDER_API")
TIMEOUT_SECONDS = 8

# Adjust these values to match the actual Order Service enum in OutSystems.
ORDER_STATUS_CODES = {
    1: "CREATED",
    2: "ARRIVED",
    3: "ARRIVED_OUTSIDE_OPERATION_TIME",
    4: "NO_SHOW",
    5: "HANDED_OVER",
    9: "PENDING_PAYMENT",
    10: "PAYMENT_FAILED"
}


ALLOWED_FINAL_STATUSES = {4, 5}


# -----------------------------------------------
# Helpers
# -----------------------------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def order_headers() -> dict:
    return {"Content-Type": "application/json"}


# -----------------------------------------------
# Arrow 1, 2: Get Active Pickups
# Merchant App -> Merchant Management -> Order
# -----------------------------------------------
@app.route('/pickup', methods=['GET'])
def get_active_pickups():
    """
    Get all active pickups
    ---
    responses:
      200:
        description: List of orders with status CREATED or ARRIVED
        schema:
          type: object
          properties:
            success:
              type: boolean
            count:
              type: integer
            active_pickups:
              type: array
              items:
                type: object
      500:
        description: Order service failure
    """
    try:
        response = requests.get(
            f"{ORDER_API_URL}/order",
            headers=order_headers(),
            timeout=TIMEOUT_SECONDS,
        )

        if response.status_code == 200:
            active_orders = response.json()['data'] 

            return jsonify({
                "success": True,
                "active_pickups": active_orders,
                "count": len(active_orders)
            }), 200

        return jsonify({
            "success": False,
            "message": "Failed to fetch orders from Order service",
            "status_code": response.status_code,
            "details": response.text,
        }), 500

    except requests.RequestException as e:
        return jsonify({
            "success": False,
            "message": f"Order service request failed: {str(e)}"
        }), 500


# -----------------------------------------------
# Arrow 3, 6: Complete / No-Show Pickup
# Merchant App -> Merchant Management -> Order
# -----------------------------------------------
@app.route('/pickup', methods=['PUT'])
def update_pickup_status():
    """
    Update order status to HANDED_OVER or NO_SHOW
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            order_id:
              type: integer
              example: 1
            order_status:
              type: integer
              example: 5
            merchant_id:
              type: integer
              example: 1
            sc_id:
              type: integer
              example: 1
    responses:
      200:
        description: Successfully updated order status
      400:
        description: Invalid status provided
      404:
        description: Order not found
      500:
        description: Order service update rejected or failed
    """
    try:
        data = request.get_json(silent=True) or {}
        order_id = data.get('order_id')
        status_id = data.get('order_status')
        merchant_id = data.get('merchant_id')

        # Validation: Ensure the status ID exists in our allowed final statuses
        # Note: If ALLOWED_FINAL_STATUSES contains strings, use ORDER_STATUS_CODES to check
        if status_id not in ALLOWED_FINAL_STATUSES:
            return jsonify({
                "success": False,
                "message": f"Invalid status ID: {status_id}. Allowed values: HANDED_OVER, NO_SHOW"
            }), 400 

        # Step 1: Verify record exists
        get_response = requests.get(
            f"{ORDER_API_URL}/order/{merchant_id}/{order_id}",
            headers=order_headers(),
            timeout=TIMEOUT_SECONDS,
        )
        
        if get_response.status_code != 200:
            return jsonify({
                "success": False,
                "message": "Failed to fetch order from Order service",
                "status_code": get_response.status_code
            }), 500

        existing_data = get_response.json()
        if not existing_data or existing_data.get('data', {}).get('order_id') == 0:
            return jsonify({
                "success": False,
                "message": f"Order record {order_id} not found"
            }), 404

        # Step 2 & 3: Forward the received data directly to the Order Service
        put_response = requests.put(
            f"{ORDER_API_URL}/order",
            json=data,
            headers=order_headers(),
            timeout=TIMEOUT_SECONDS,
        )

        if put_response.status_code in [200, 201, 204] or put_response.text == "true":
            response_body = put_response.json() if (put_response.text and put_response.text not in ["true", "false"]) else put_response.text
            
            status_name = ORDER_STATUS_CODES.get(status_id, "UNKNOWN")

            return jsonify({
                "success": True,
                "message": f"Order record {order_id} updated to {status_name}",
                "merchant_action": status_name,
                "order_service_response": response_body,
            }), 200

        return jsonify({
            "success": False,
            "message": "Order service rejected the update",
            "status_code": put_response.status_code,
            "details": put_response.text
        }), 500

    except requests.RequestException as e:
        return jsonify({"success": False, "message": f"Network error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# -----------------------------------------------
# Health Check
# -----------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    ---
    responses:
      200:
        description: Service status
        schema:
          type: object
          properties:
            status:
              type: string
            service:
              type: string
    """
    return jsonify({
        "status": "running",
        "service": "Merchant Management Service",
        "port": 5001
    }), 200


# -----------------------------------------------
# Run
# -----------------------------------------------
if __name__ == '__main__':
    app.run(port=5001, debug=True)