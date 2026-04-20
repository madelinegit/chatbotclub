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
from app.api.instagram_auth_routes import router as instagram_auth_router
from app.api.threads_auth_routes import router as threads_auth_router
from app.api.admin_app_routes import router as admin_app_router


def _auto_post_job():
    """Generate a post and add it to the approval queue. Does NOT auto-post."""
    try:
        from app.services.social_service import generate_post_for_queue
        from app.services.local_context_service import get_local_context

        context = get_local_context()
        result  = generate_post_for_queue(local_context=context)
        if not result:
            print("CRON: post generation failed")
            return
        print(f"CRON: queued post #{result['id']} for approval — {result['caption'][:60]}")

        try:
            from app.services.push_service import send_push
            send_push(
                title="New post ready",
                body=result["caption"][:100],
                url="/admin/app",
                tag="new-post",
            )
        except Exception as push_err:
            print(f"CRON: push notification failed (non-fatal): {push_err}")
    except Exception as e:
        print(f"CRON ERROR: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    print("CRON: scheduler disabled — posts are manual only")

    yield


app = FastAPI(title="Maya AI", redirect_slashes=False, lifespan=lifespan)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(payment_router)
app.include_router(profile_router)
app.include_router(blog_router)
app.include_router(admin_router)
app.include_router(instagram_auth_router)
app.include_router(threads_auth_router)
app.include_router(admin_app_router)

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

@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html", {})

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
