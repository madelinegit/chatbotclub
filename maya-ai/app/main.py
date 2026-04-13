from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.chat_routes import router as chat_router
from app.api.auth_routes import router as auth_router
from app.api.payment_routes import router as payment_router
from app.api.profile_routes import router as profile_router
from app.api.admin_routes import router as admin_router
from app.api.blog_routes import router as blog_router
from app.db.database import init_db

app = FastAPI(title="Maya AI")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(payment_router)
app.include_router(profile_router)
app.include_router(admin_router)
app.include_router(blog_router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(request, "landing.html", {})

@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html", {})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})

@app.get("/age-verify", response_class=HTMLResponse)
def age_verify_page(request: Request):
    return templates.TemplateResponse(request, "age_verify.html", {})

@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    return templates.TemplateResponse(request, "profile.html", {})

@app.get("/blog", response_class=HTMLResponse)
def blog_page(request: Request):
    return templates.TemplateResponse(request, "blog.html", {})

@app.get("/blog/{slug}", response_class=HTMLResponse)
def blog_post_page(request: Request, slug: str):
    return templates.TemplateResponse(request, "blog_post.html", {"slug": slug})

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse(request, "pricing.html", {})

@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return templates.TemplateResponse(request, "terms.html", {})

@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})