from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from app.models.schemas import RegisterRequest, LoginRequest, AuthResponse
from app.services.auth_service import register, login

router = APIRouter(prefix="/api/auth")


@router.get("/callback", response_class=HTMLResponse)
def auth_callback(code: str = None, error: str = None, error_description: str = None):
    """Handle Supabase email confirmation redirects."""
    if error:
        return HTMLResponse(f"""
        <html><head><title>Link Expired</title>
        <style>body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#0e0e11;color:#e0ddd8;}}
        .box{{text-align:center;padding:40px;}}.btn{{display:inline-block;margin-top:20px;padding:12px 28px;background:#c9a96e;color:#000;border-radius:8px;text-decoration:none;font-weight:600;}}</style>
        </head><body><div class="box"><h2>Link expired or invalid</h2>
        <p style="color:#888">{error_description or error}</p>
        <a class="btn" href="/">Go to Maya</a></div></body></html>
        """, status_code=400)

    # Code is present — email confirmed successfully
    return HTMLResponse("""
    <html><head><title>Email Confirmed</title>
    <style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#0e0e11;color:#e0ddd8;}
    .box{text-align:center;padding:40px;}.btn{display:inline-block;margin-top:20px;padding:12px 28px;background:#c9a96e;color:#000;border-radius:8px;text-decoration:none;font-weight:600;}</style>
    </head><body><div class="box">
    <h2>You're confirmed.</h2>
    <p style="color:#888">Your email has been verified. You can now sign in.</p>
    <a class="btn" href="/">Talk to Maya</a>
    </div></body></html>
    """)

EMAIL_VERIFY_MSG = "Account created. Please check your email to verify your address, then sign in."


@router.post("/register")
def register_user(data: RegisterRequest):
    try:
        result = register(email=data.email, password=data.password)
        return AuthResponse(**result)
    except ValueError as e:
        detail = str(e)
        if detail == EMAIL_VERIFY_MSG:
            return JSONResponse(status_code=200, content={"verify_email": True, "detail": detail})
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=AuthResponse)
def login_user(data: LoginRequest):
    try:
        result = login(email=data.email, password=data.password)
        return AuthResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")
