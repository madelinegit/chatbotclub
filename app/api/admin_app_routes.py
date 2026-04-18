"""Mobile admin app — /admin/app"""
import os
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router       = APIRouter(prefix="/admin/app")
templates    = Jinja2Templates(directory="templates")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me-admin")


def _check(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden.")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_app_page(request: Request):
    return templates.TemplateResponse(request, "admin_app.html", {})


@router.post("/setup-vapid")
def setup_vapid(secret: str = Query(...)):
    _check(secret)
    from app.services.push_service import generate_vapid_keys
    return generate_vapid_keys()


@router.get("/vapid-public-key")
def vapid_public_key(secret: str = Query(...)):
    _check(secret)
    from app.services.push_service import get_vapid_public_key
    key = get_vapid_public_key()
    if not key:
        raise HTTPException(status_code=404, detail="VAPID not set up yet.")
    return {"public_key": key}


@router.post("/subscribe")
async def subscribe_push(secret: str = Query(...), request: Request = None):
    _check(secret)
    body     = await request.json()
    endpoint = body.get("endpoint")
    keys     = body.get("keys", {})
    p256dh   = keys.get("p256dh")
    auth     = keys.get("auth")
    if not endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="endpoint and keys required.")
    from app.services.push_service import save_subscription
    save_subscription(endpoint, p256dh, auth)
    return {"status": "subscribed"}


@router.post("/push-test")
def push_test(secret: str = Query(...)):
    _check(secret)
    from app.services.push_service import send_push
    sent = send_push("Maya Admin", "Push notifications are working!")
    if sent == 0:
        raise HTTPException(status_code=422, detail="No subscriptions found or VAPID not set up.")
    return {"status": "sent", "count": sent}
