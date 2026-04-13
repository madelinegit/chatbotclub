import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.api.chat_routes import get_current_user
from app.db.crud import (
    get_profile, update_profile, get_credit_balance,
    get_transactions, get_all_messages, set_age_verified, is_age_verified
)

router = APIRouter(prefix="/api/profile")

AVATAR_DIR = "static/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)


@router.get("/me")
def get_my_profile(user: dict = Depends(get_current_user)):
    profile = get_profile(user["user_id"]) or {}
    balance = get_credit_balance(user["user_id"])
    return {
        "user_id":      user["user_id"],
        "email":        user["email"],
        "display_name": profile.get("display_name"),
        "bio":          profile.get("bio"),
        "avatar_url":   profile.get("avatar_url"),
        "credits":      balance,
        "age_verified": is_age_verified(user["user_id"]),
    }


@router.post("/update")
async def update_my_profile(
    display_name: str = Form(None),
    bio: str = Form(None),
    avatar: UploadFile = File(None),
    user: dict = Depends(get_current_user),
):
    avatar_url = None

    if avatar and avatar.filename:
        ext     = os.path.splitext(avatar.filename)[1].lower()
        allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Invalid image type.")

        content = await avatar.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large. Max 5MB.")

        filename = f"{user['user_id']}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(AVATAR_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(content)

        avatar_url = f"/static/avatars/{filename}"

    update_profile(
        user_id=user["user_id"],
        display_name=display_name,
        bio=bio,
        avatar_url=avatar_url,
    )

    return {"status": "ok", "avatar_url": avatar_url}


@router.get("/history")
def chat_history(user: dict = Depends(get_current_user)):
    return {"messages": get_all_messages(user["user_id"])}


@router.get("/transactions")
def transaction_history(user: dict = Depends(get_current_user)):
    return {"transactions": get_transactions(user["user_id"])}


@router.post("/verify-age")
def verify_age(user: dict = Depends(get_current_user)):
    set_age_verified(user["user_id"])
    return {"status": "ok", "age_verified": True}
