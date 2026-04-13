from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY
from app.db.crud import create_user, add_credits

# 10 free credits on signup — enough to get hooked, not enough to be satisfied
STARTER_CREDITS = 10


def _client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def register(email: str, password: str) -> dict:
    """Create a Supabase auth user, mirror in local DB, give starter credits."""
    sb = _client()
    response = sb.auth.sign_up({"email": email, "password": password})

    if response.user is None:
        raise ValueError("Registration failed. Email may already be in use.")

    user_id = response.user.id
    create_user(user_id=user_id, email=email)
    add_credits(user_id=user_id, amount=STARTER_CREDITS)

    if response.session is None:
        # Supabase email confirmation is enabled — user must verify before logging in.
        raise ValueError("Account created. Please check your email to verify your address, then sign in.")

    return {
        "access_token": response.session.access_token,
        "user_id":      user_id,
        "email":        email,
    }


def login(email: str, password: str) -> dict:
    """Sign in via Supabase and return access token."""
    sb = _client()
    response = sb.auth.sign_in_with_password({"email": email, "password": password})

    if response.user is None:
        raise ValueError("Invalid email or password.")

    return {
        "access_token": response.session.access_token,
        "user_id":      response.user.id,
        "email":        response.user.email,
    }


def get_user_from_token(token: str) -> dict:
    """Validate a bearer token and return the user payload."""
    sb = _client()
    response = sb.auth.get_user(token)

    if response.user is None:
        raise ValueError("Invalid or expired token.")

    return {
        "user_id": response.user.id,
        "email":   response.user.email,
    }
