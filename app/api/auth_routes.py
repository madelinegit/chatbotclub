from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.schemas import RegisterRequest, LoginRequest, AuthResponse
from app.services.auth_service import register, login

router = APIRouter(prefix="/api/auth")

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
