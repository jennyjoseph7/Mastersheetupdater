import datetime
import razorpay
import autocrm_validator
import sys, os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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

def get_dealer_model():
    return gryd.base_model.Model("dealership", AUTOCRM_APP_ENTERPRISE_ID)

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

def get_dealer_by_id(dealer_id: str):
    DealerModel = get_dealer_model()

    result = DealerModel.list(
        dealership_id=str(dealer_id),
        _as_option=True
    )

    if not result:
        logger.error(f"[Dealership Id] Not found | dealership_id={dealer_id}")
        raise Exception("Dealership Id record not found")

    return result[0]

def create_credit_purchase(dealership_id: str, credits: int, currency="INR"):
    from core import VATCalculator, calculate_currency_rate

    try:
        from .core import VATCalculator, calculate_currency_rate
    except ImportError:
        from core import VATCalculator, calculate_currency_rate
    if not isinstance(credits, int) or credits <= 0:
        raise ValueError("Credits must be a positive integer")

    dealer = get_dealer_by_id(dealership_id)

    # Determine the highest discount
    final_discount_pct = max(dealer.get("region_discount_percentage", 0),
                             dealer.get("discount_percentage", 0))

    # Get currency rate
    currency_rate_obj = calculate_currency_rate(currency)
    unit_price = currency_rate_obj["rate"]

    # VAT calculation
    vat_calculator = VATCalculator("india")
    final_cost_obj = vat_calculator.calculate(
        item_quantity=credits,
        item_price=unit_price,
        discount_percentage=final_discount_pct
    )

    # Use total_amount from VAT calculator (includes taxes)
    total_amount = final_cost_obj["total_amount"]

    ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND"}

    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        amount_gateway = int(total_amount)
    else:
        amount_gateway = int(round(total_amount * 100))

    order = client.order.create({
        "amount": amount_gateway,
        "currency": currency,
        "payment_capture": 1
    })

    BillingModel = get_billing_model()

    billing_obj = {
        "dealership_id": dealership_id,
        "transaction_date": datetime.date.today().isoformat(),
        "transaction_type": "credit",
        "item_name": "credits_purchase",
        "item_description": "Purchasing credits",
        "item_quantity": credits,
        "item_price": unit_price,
        "item_total": final_cost_obj["item_final_total"],   # after discount, before tax
        "item_units": "credits",
        "currency": currency,
        "payment_gateway": "razorpay",
        "razorpay_order_id": order["id"],
        "amount_paise": amount_gateway if currency.upper() == "INR" else None,
        "status": "initiated",
        "channel": "razorpay",
        "campaign_id": "inbound",
        "discount_percentage": final_discount_pct,
        "item_final_price" : total_amount,
        "discount_amount": 0,
        "item_final_total": total_amount,
    }

    # Merge VAT calculation
    billing_obj.update(final_cost_obj)

    billing = BillingModel.post(billing_obj)

    logger.info(
        f"[BILLING] Initiated | billing_id={billing['billing_id']} | order_id={order['id']}"
    )

    return {
        "order_id": order["id"],
        "credits": credits,
        "currency": currency,
        "amount": total_amount
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
    logger.info("[PAYMENT] confirm_payment_success called | webhook=%s | payload=%s", webhook, data)

    order_id = data["razorpay_order_id"]
    logger.info("[PAYMENT] Processing order_id=%s", order_id)

    if not webhook:
        logger.info("[PAYMENT] Verifying Razorpay signature for order=%s", order_id)

        if not verify_payment_signature(data):
            logger.error("[PAYMENT] Invalid payment signature | order=%s | payload=%s", order_id, data)
            raise Exception("Invalid payment signature")

        logger.info("[PAYMENT] Signature verified successfully | order=%s", order_id)

        payment = client.payment.fetch(data["razorpay_payment_id"])
        logger.info(
            "[PAYMENT] Payment fetched from Razorpay | payment_id=%s | status=%s",
            payment["id"],
            payment["status"]
        )

    else:
        payment = data["payment"]
        logger.info(
            "[PAYMENT] Webhook payment received | payment_id=%s | status=%s",
            payment.get("id"),
            payment.get("status")
        )

    if payment["status"] not in ["authorized", "captured"]:
        logger.warning(
            "[PAYMENT] Ignoring payment due to invalid status | payment_id=%s | status=%s",
            payment["id"],
            payment["status"]
        )
        return

    logger.info("[PAYMENT] Fetching billing record | order_id=%s", order_id)
    billing = get_billing_by_order_id(order_id)

    if not billing:
        logger.error("[PAYMENT] Billing record not found | order_id=%s", order_id)
        raise Exception("Billing record not found")

    logger.info(
        "[PAYMENT] Billing fetched | billing_id=%s | status=%s | expected_amount=%s",
        billing["billing_id"],
        billing["status"],
        billing["amount_paise"]
    )

    if billing["status"] == "success":
        logger.warning(
            "[PAYMENT] Billing already marked successful | billing_id=%s | order_id=%s",
            billing["billing_id"],
            order_id
        )
        return

    logger.info(
        "[PAYMENT] Validating payment amount | razorpay_amount=%s | expected_amount=%s",
        payment["amount"],
        billing["amount_paise"]
    )

    if payment["amount"] != billing["amount_paise"]:
        logger.error(
            "[PAYMENT] Amount mismatch | order_id=%s | razorpay_amount=%s | expected=%s",
            order_id,
            payment["amount"],
            billing["amount_paise"]
        )
        raise Exception("Amount mismatch")

    logger.info(
        "[PAYMENT] Creating async billing task | dealership=%s | credits=%s",
        billing["dealership_id"],
        billing["item_quantity"]
    )

    gryd.create_async_task(
        "post_billing",
        "autocrm-core",
        kwargs={
            "dealership_id": billing["dealership_id"],
            "transaction_type": "credit",
            "item_name": billing["item_name"],
            "item_description": billing.get("item_description"),
            "transaction_date": datetime.date.today().isoformat(),
            "item_quantity": billing["item_quantity"],
            "item_price": billing["item_price"],
            "item_unit": "credits",
            "currency": "credits",
            "campaign_id": "inbound",
            "channel": "razorpay",

            "billing_id": billing["billing_id"],
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment["id"],
            "razorpay_signature": data.get("razorpay_signature"),
            "raw_razorpay_payload": payment,
        }
    )

    logger.info(
        "[CREDITS] Credited | dealership=%s | credits=%s | order=%s | payment_id=%s",
        billing["dealership_id"],
        billing["item_quantity"],
        order_id,
        payment["id"]
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
        confirm_payment_success({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": entity["id"],
            "razorpay_signature": payload.get("signature", ""),
            "payment" : payment
        }, webhook = True)

    elif event == "payment.failed":
        mark_payment_failed(order_id, entity.get("error_description", ""))

    elif event == "payment.cancelled":
        mark_payment_cancelled(order_id)


def calculate_pricing(
    credits_purchased,
    alpha=0.5,
    min_credits_for_discount=100_000,
    cap_discount=0.2,
    credits_at_cap=10_000_000,
    price_per_credit=1.0
):
    """
    Returns pricing details for a credit purchase using a capped power-curve discount.

    Returns:
        dict: {
            "credits_purchased": int,
            "discount": float,      # fraction (e.g., 0.2 = 20%)
            "item_cost": float      # total cost after discount
        }
    """

    # No discount below minimum threshold
    if credits_purchased < min_credits_for_discount:
        discount = 0.0
    elif credits_purchased >= credits_at_cap:
        discount = cap_discount
    else:
        normalized = (
            (credits_purchased - min_credits_for_discount) /
            (credits_at_cap - min_credits_for_discount)
        )
        discount = cap_discount * (normalized ** alpha)

    item_cost = credits_purchased * price_per_credit * (1 - discount)

    return {
        "credits_purchased": credits_purchased,
        "discount": round(discount, 6),
        "item_cost": round(item_cost, 2)
    }