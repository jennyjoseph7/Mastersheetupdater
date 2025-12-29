import datetime
import razorpay
import autocrm_validator
from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CORE_SERVICE_NAME, gryd

gryd.SERVICE = AUTOCRM_CORE_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

BillingModel = gryd.base_model.Model("billing", AUTOCRM_APP_ENTERPRISE_ID)

def get_billing_by_order_id(order_id: str):
    result = BillingModel.list(razorpay_order_id=order_id, _as_option=True)
    if not result:
        logger.error(f"[BILLING] Not found | order_id={order_id}")
        raise Exception("Billing record not found")
    return result[0]

def create_credit_purchase(dealership_id: str, credits: int):
    
    if not isinstance(credits, int) or credits <= 0:
        raise ValueError("Credits must be a positive integer (INR)")

    amount_paise = credits * 100
    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1
    })

    billing = BillingModel.post({
        "dealership_id": dealership_id,
        "transaction_date": datetime.date.today().isoformat(),
        "transaction_type": "credit",
        "item_name": "credits_purchase",
        "item_quantity": credits,
        "item_price": 1,
        "currency": "INR",
        "payment_gateway": "razorpay",
        "razorpay_order_id": order["id"],
        "amount_paise": amount_paise,
        "status": "initiated"
    })

    logger.info(f"[BILLING] Initiated | billing_id={billing['billing_id']} | order_id={order['id']}")
    return {
        "order_id": order["id"],
        "credits": credits
    }

def verify_payment_signature(data: dict) -> bool:
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })
        return True
    except Exception as e:
        logger.error(f"[SECURITY] Signature verification failed | {e}")
        return False

def confirm_payment_success(data: dict):
    
    order_id = data["razorpay_order_id"]

    if not verify_payment_signature(data):
        raise Exception("Invalid payment signature")

    payment = client.payment.fetch(data["razorpay_payment_id"])

    if payment["status"] != "captured":
        raise Exception(f"Payment not captured | status={payment['status']}")

    if payment["currency"] != "INR":
        raise Exception("Currency mismatch")

    billing = get_billing_by_order_id(order_id)

    if billing["status"] == "success":
        logger.warning(f"[PAYMENT] Duplicate success ignored | billing_id={billing['billing_id']}")
        return

    if payment["amount"] != billing["amount_paise"]:
        raise Exception("Amount mismatch")

    BillingModel.post({
            "billing_id": billing["billing_id"],
            "status": "success",
            "razorpay_payment_id": payment["id"],
            "razorpay_signature": data["razorpay_signature"],
            "raw_razorpay_payload": payment
        })

    logger.info(f"[CREDITS] Updated | billing_id={billing['billing_id']} | credits={billing['item_quantity']}")

def mark_payment_failed(order_id: str, reason: str = ""):
    billing = get_billing_by_order_id(order_id)

    if billing["status"] in ["success", "failed"]:
        logger.info(f"[PAYMENT] Ignored duplicate failure | billing_id={billing['billing_id']}")
        return

    BillingModel.post({
        "billing_id": billing["billing_id"],
        "status": "failed",
        "remarks": reason or "Payment failed or cancelled"
    })

    logger.warning(f"[PAYMENT] Failed | billing_id={billing['billing_id']} | reason={reason}")

def mark_payment_cancelled(order_id: str):
    billing = get_billing_by_order_id(order_id)

    if billing["status"] != "initiated":
        return

    BillingModel.post({
        "billing_id": billing["billing_id"],
        "status": "cancelled",
        "remarks": "User cancelled payment"
    })

    logger.info(f"[PAYMENT] Cancelled | billing_id={billing['billing_id']}")

def razorpay_webhook_handler(payload: dict):
    event = payload.get("event")
    entity = payload["payload"]["payment"]["entity"]
    order_id = entity["order_id"]

    if event == "payment.captured":
        confirm_payment_success({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": entity["id"],
            "razorpay_signature": payload.get("signature", "")
        })
    elif event == "payment.failed":
        mark_payment_failed(order_id, entity.get("error_description", ""))
    elif event == "payment.cancelled":
        mark_payment_cancelled(order_id)
