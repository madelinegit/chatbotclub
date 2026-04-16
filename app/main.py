from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request

from app.db.database import init_db
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.payment_routes import router as payment_router
from app.api.profile_routes import router as profile_router
from app.api.blog_routes import router as blog_router
from app.api.admin_routes import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Maya AI", redirect_slashes=False, lifespan=lifespan)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(payment_router)
app.include_router(profile_router)
app.include_router(blog_router)
app.include_router(admin_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@app.get("/debug")
def debug(request: Request):
    return JSONResponse({
        "url": str(request.url),
        "scheme": request.url.scheme,
        "headers": dict(request.headers),
    })


@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(request, "landing.html", {})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse(request, "pricing.html", {})

@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return templates.TemplateResponse(request, "terms.html", {})

@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})
