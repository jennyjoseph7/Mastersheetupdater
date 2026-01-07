import datetime
import razorpay
import autocrm_validator

from config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
    AUTOCRM_APP_ENTERPRISE_ID,
    AUTOCRM_CORE_SERVICE_NAME,
    gryd
)

gryd.SERVICE = AUTOCRM_CORE_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def get_billing_model():
    return gryd.base_model.Model("billing", AUTOCRM_APP_ENTERPRISE_ID)

def get_billing_by_order_id(order_id: str):
    BillingModel = get_billing_model()

    result = BillingModel.list(
        razorpay_order_id=str(order_id),
        _as_option=True
    )

    if not result:
        logger.error(f"[BILLING] Not found | order_id={order_id}")
        raise Exception("Billing record not found")

    return result[0]

def create_credit_purchase(dealership_id: str, credits: int):

    if not isinstance(credits, int) or credits <= 0:
        raise ValueError("Credits must be a positive integer")

    amount_paise = credits * 100

    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1
    })

    BillingModel = get_billing_model()

    billing = BillingModel.post({
        "dealership_id": dealership_id,
        "transaction_date": datetime.date.today().isoformat(),
        "transaction_type": "credit",
        "item_name": "credits_purchase",
        "item_quantity": credits,
        "item_price": 1,
        "item_total" : credits,
        "item_units": "credits",
        "currency": "INR",
        "payment_gateway": "razorpay",
        "razorpay_order_id": order["id"],
        "amount_paise": amount_paise,
        "status": "initiated",
        "channel" : "razorpay",
        "campaing_id" : "inbound",
        "item_description" : "Purchasing credits"
    })

    logger.info(
        f"[BILLING] Initiated | billing_id={billing['billing_id']} | order_id={order['id']}"
    )

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

def confirm_payment_success(data: dict, webhook=False):
    order_id = data["razorpay_order_id"]

    if not webhook:
        if not verify_payment_signature(data):
            raise Exception("Invalid payment signature")
        payment = client.payment.fetch(data["razorpay_payment_id"])
    else:
        payment = data["payment"]

    if payment["status"] != "authorized" and payment["status"] != "captured":
        return  
    
    billing = get_billing_by_order_id(order_id)

    if billing["status"] == "success":
        return

    if payment["amount"] != billing["amount_paise"]:
        raise Exception("Amount mismatch")
    
    # yield { 
    #     "_job":{
    #         "task": "post_billing",
    #         "service": "autocrm-core",
    #         "kwargs": {
    #             "dealership_id": billing["dealership_id"],
    #             "transaction_type": "credit",
    #             "item_name": billing["item_name"],
    #             "item_description": billing.get("item_description"),
    #             "transaction_date": datetime.date.today().isoformat(),
    #             "item_quantity": billing["item_quantity"],
    #             "item_price": billing["item_price"],
    #             "item_unit": "credits",
    #             "currency": "credits",
    #             "campaign_id": "inbound",
    #             "channel": "razorpay",

    #             "billing_id": billing["billing_id"],
    #             "razorpay_order_id": order_id,
    #             "razorpay_payment_id": payment["id"],
    #             "razorpay_signature": data["razorpay_signature"],
    #             "raw_razorpay_payload": payment,
    #         }
    #     }
    # }

    from core.core import post_billing

    post_billing(
        dealership_id=billing["dealership_id"],
        transaction_type="credit",
        item_name=billing["item_name"],
        item_description=billing.get("item_description"),
        transaction_date=datetime.date.today().isoformat(),
        item_quantity=billing["item_quantity"],
        item_price=billing["item_price"],
        item_unit="credits",
        currency="credits",
        campaign_id="inbound",
        channel="razorpay",
        billing_id = billing["billing_id"],
        razorpay_order_id=order_id,
        razorpay_payment_id=payment["id"],
        razorpay_signature=data["razorpay_signature"],
        raw_razorpay_payload=payment
    )

    logger.info(
        f"[CREDITS] Credited | dealership={billing['dealership_id']} "
        f"| credits={billing['item_quantity']} | order={order_id}"
    )

def mark_payment_failed(order_id: str, reason: str = ""):
    BillingModel = get_billing_model()
    billing = get_billing_by_order_id(order_id)

    if billing["status"] in ["success", "failed"]:
        logger.info(
            f"[PAYMENT] Ignored duplicate failure | billing_id={billing['billing_id']}"
        )
        return

    BillingModel.post({
        "billing_id": billing["billing_id"],
        "status": "failed",
        "remarks": reason or "Payment failed or cancelled"
    })

    logger.warning(
        f"[PAYMENT] Failed | billing_id={billing['billing_id']} | reason={reason}"
    )


def mark_payment_cancelled(order_id: str):
    BillingModel = get_billing_model()
    billing = get_billing_by_order_id(order_id)

    if billing["status"] != "initiated":
        return

    BillingModel.post({
        "billing_id": billing["billing_id"],
        "status": "cancelled",
        "remarks": "User cancelled payment"
    })

    logger.info(
        f"[PAYMENT] Cancelled | billing_id={billing['billing_id']}"
    )

def razorpay_webhook_handler(payload: dict):
    event = payload.get("event")
    payment = payload["payload"]["payment"]["entity"]
    entity = payload["payload"]["payment"]["entity"]
    order_id = entity["order_id"]

    if event == "payment.captured":
        return confirm_payment_success({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": entity["id"],
            "razorpay_signature": payload.get("signature", ""),
            "payment" : payment
        }, webhook = True)

    elif event == "payment.failed":
        mark_payment_failed(order_id, entity.get("error_description", ""))

    elif event == "payment.cancelled":
        mark_payment_cancelled(order_id)
