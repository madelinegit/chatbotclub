from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty.")
        if len(v) > 1000:
            raise ValueError("Message too long. Max 1000 characters.")
        return v


class ChatResponse(BaseModel):
    reply: str
    followup: Optional[str] = None


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: str
    email: str


# ── Credits ───────────────────────────────────────────────────────────────────

class CreditBalanceResponse(BaseModel):
    user_id: str
    balance: int


class PurchaseRequest(BaseModel):
    package: str  # e.g. "starter", "popular", "premium"


# ── User ──────────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    user_id: str
    email: str
    credit_balance: int
