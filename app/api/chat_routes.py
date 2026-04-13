import asyncio
import random

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.ai.chat import generate_reply
from app.models.schemas import ChatRequest, ChatResponse
from app.services.auth_service import get_user_from_token
from app.services.rate_limiter import is_rate_limited
from app.services.payment_service import COST_MESSAGE, COST_IMAGE
from app.db.crud import get_credit_balance, deduct_credit, is_age_verified, is_dev_user

router = APIRouter(prefix="/api")
bearer = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return get_user_from_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _is_image_request(message: str) -> bool:
    IMAGE_TRIGGERS = [
        "show me you", "show me a pic", "show me a photo", "show me a picture",
        "show me what you look like", "show me yourself", "let me see you",
        "can i see you", "send me a pic", "send me a photo", "send me a picture",
        "send a pic", "send a photo", "send a picture", "drop a pic",
        "take a pic", "take a photo", "pic of you", "photo of you",
        "what do you look like", "show yourself", "snap a pic", "got any pics",
    ]
    lowered = message.lower()
    return any(t in lowered for t in IMAGE_TRIGGERS)


@router.post("/chat", response_model=ChatResponse)
async def chat(data: ChatRequest, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]

    dev = is_dev_user(user_id)

    # Age verification gate (bypassed for dev users)
    if not dev and not is_age_verified(user_id):
        raise HTTPException(status_code=403, detail="AGE_UNVERIFIED")

    # Rate limit
    if is_rate_limited(user_id):
        raise HTTPException(status_code=429, detail="Too many messages. Slow down.")

    # Determine credit cost for this request
    cost = COST_IMAGE if _is_image_request(data.message) else COST_MESSAGE

    if not dev:
        # Check balance
        if get_credit_balance(user_id) < cost:
            raise HTTPException(
                status_code=402,
                detail=f"Not enough credits. This costs {cost} credit{'s' if cost > 1 else ''}."
            )

    reply = generate_reply(user_id, data.message)

    if not dev:
        # Deduct credits only after a successful reply
        for _ in range(cost):
            deduct_credit(user_id)

    await asyncio.sleep(random.uniform(2, 5))

    if random.random() < 0.4 and len(reply) > 80:
        sentences = (
            reply.replace("? ", "?|").replace("! ", "!|").replace(". ", ".|").split("|")
        )
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) >= 2:
            return ChatResponse(reply=sentences[0], followup=" ".join(sentences[1:]))

    return ChatResponse(reply=reply)
