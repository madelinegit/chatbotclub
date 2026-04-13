from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.chat_routes import get_current_user
from app.models.schemas import CreditBalanceResponse, PurchaseRequest
from app.services.payment_service import (
    get_packages, handle_ccbill_webhook,
    build_payment_url, get_credit_costs
)
from app.db.crud import get_credit_balance

router = APIRouter(prefix="/api/payments")


@router.get("/packages")
def list_packages():
    """Return available credit packages with full descriptions."""
    return get_packages()


@router.get("/costs")
def credit_costs():
    """Return how many credits each action costs."""
    return get_credit_costs()


@router.get("/balance", response_model=CreditBalanceResponse)
def credit_balance(user: dict = Depends(get_current_user)):
    balance = get_credit_balance(user["user_id"])
    return CreditBalanceResponse(user_id=user["user_id"], balance=balance)


@router.post("/purchase")
def purchase(data: PurchaseRequest, user: dict = Depends(get_current_user)):
    try:
        url = build_payment_url(user_id=user["user_id"], package_key=data.package)
        return {"payment_url": url}
    except NotImplementedError:
        raise HTTPException(
            status_code=503,
            detail="Payment processing coming soon. Check back shortly.",
        )


@router.post("/webhook/ccbill")
async def ccbill_webhook(request: Request):
    payload = await request.form()
    success = handle_ccbill_webhook(dict(payload))
    if not success:
        raise HTTPException(status_code=400, detail="Webhook processing failed.")
    return {"status": "ok"}
