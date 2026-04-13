"""
CCBill payment service.
Placeholder until CCBill account is approved.
"""
from app.config import CCBILL_ACCOUNT_NUM, CCBILL_SUBACCOUNT, CCBILL_SECRET_KEY
from app.db.crud import add_credits, log_transaction

# ── Credit cost per action ────────────────────────────────────────────────────
COST_MESSAGE = 1   # credits per text message
COST_IMAGE   = 3   # credits per image generation (costs more API-side)

# ── Credit packages ───────────────────────────────────────────────────────────
# Each entry: credits granted, price in cents, display label, badge
PACKAGES = {
    "starter": {
        "credits":      50,
        "amount_cents": 999,
        "label":        "Starter",
        "description":  "50 messages or ~16 images",
        "badge":        None,
    },
    "popular": {
        "credits":      150,
        "amount_cents": 2499,
        "label":        "Popular",
        "description":  "150 messages or ~50 images",
        "badge":        "BEST VALUE",
    },
    "premium": {
        "credits":      400,
        "amount_cents": 5999,
        "label":        "Premium",
        "description":  "400 messages or ~133 images",
        "badge":        None,
    },
}


def get_packages() -> dict:
    return PACKAGES


def get_credit_costs() -> dict:
    """Return per-action credit costs so frontend can display them."""
    return {
        "message": COST_MESSAGE,
        "image":   COST_IMAGE,
    }


def handle_ccbill_webhook(payload: dict) -> bool:
    """Process an incoming CCBill webhook POST on successful charge."""
    user_id       = payload.get("X-user-id")
    processor_ref = payload.get("subscriptionId")
    billed_amount = payload.get("billedAmount", "0")
    package_key   = payload.get("X-package")

    if not user_id or not package_key:
        return False

    package = PACKAGES.get(package_key)
    if not package:
        return False

    add_credits(user_id=user_id, amount=package["credits"])
    log_transaction(
        user_id=user_id,
        amount_cents=int(float(billed_amount) * 100),
        credits_added=package["credits"],
        processor_ref=processor_ref,
    )
    return True


def build_payment_url(user_id: str, package_key: str) -> str:
    """Generate CCBill FlexForms payment URL. TODO: implement after approval."""
    raise NotImplementedError("CCBill integration pending account approval.")
