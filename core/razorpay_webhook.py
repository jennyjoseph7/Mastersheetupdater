import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from flask import Flask, request, jsonify
import hmac
import hashlib
from razorpay_service import razorpay_webhook_handler

app = Flask(__name__)

WEBHOOK_SECRET = "AUTOBOT_DAVEAI_2025"

def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    
    generated_signature = hmac.new(
        bytes(secret, "utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, signature)


@app.route("/webhook/razorpay", methods=["POST"])
def razorpay_webhook():
    payload_body = request.data 
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(payload_body, signature, WEBHOOK_SECRET):
        return jsonify({"status": "error", "message": "Invalid signature"}), 400

    payload = request.json

    try:
        razorpay_webhook_handler(payload)  
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    app.run(port=5000, debug=True)
