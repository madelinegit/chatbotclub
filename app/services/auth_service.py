"""
Auth service — email/password auth backed by Railway PostgreSQL.
No external auth providers needed.
"""
import uuid
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

from app.config import SECRET_KEY
from app.db.crud import create_user
from app.db.database import get_connection

ALGORITHM      = "HS256"
TOKEN_EXPIRE_DAYS = 30
STARTER_CREDITS   = 10

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash(password: str) -> str:
    return pwd_ctx.hash(password)


def _verify(password: str, hashed: str) -> bool:
    return pwd_ctx.verify(password, hashed)


def _make_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def register(email: str, password: str) -> dict:
    email = email.lower().strip()

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    conn = get_connection()
    cur  = conn.cursor()

    # Check for existing account
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close(); conn.close()
        raise ValueError("An account with that email already exists. Try logging in.")

    user_id   = str(uuid.uuid4())
    pass_hash = _hash(password)

    cur.execute(
        "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
        (user_id, email, pass_hash),
    )
    cur.execute(
        "INSERT INTO credits (user_id, balance) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (user_id, STARTER_CREDITS),
    )
    cur.execute(
        "INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "access_token": _make_token(user_id, email),
        "user_id":      user_id,
        "email":        email,
    }


def login(email: str, password: str) -> dict:
    email = email.lower().strip()

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not row[1]:
        raise ValueError("Invalid email or password.")

    user_id, pass_hash = row
    if not _verify(password, pass_hash):
        raise ValueError("Invalid email or password.")

    return {
        "access_token": _make_token(user_id, email),
        "user_id":      user_id,
        "email":        email,
    }


def get_user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email   = payload.get("email")
        if not user_id:
            raise ValueError("Invalid token.")
        return {"user_id": user_id, "email": email}
    except JWTError:
        raise ValueError("Invalid or expired token.")
