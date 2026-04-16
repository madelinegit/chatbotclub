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


def _auto_post_job():
    """Generate a post and publish it to Threads automatically."""
    try:
        from app.services.social_service import generate_post_for_queue
        from app.services.local_context_service import get_local_context
        from app.services.threads_service import post_to_threads

        context = get_local_context()
        result  = generate_post_for_queue(local_context=context)
        if not result:
            print("CRON: post generation failed")
            return

        success = post_to_threads(
            post_id=result["id"],
            caption=result["caption"],
            image_url=result.get("image_url"),
        )
        if success:
            print(f"CRON: auto-posted to Threads — {result['caption'][:60]}")
        else:
            print("CRON: Threads post failed — check logs")
    except Exception as e:
        print(f"CRON ERROR: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    from apscheduler.schedulers.background import BackgroundScheduler
    import pytz
    scheduler = BackgroundScheduler(timezone=pytz.timezone("US/Pacific"))
    # Post at 10:00 AM and 7:00 PM Pacific every day
    scheduler.add_job(_auto_post_job, "cron", hour=10, minute=0)
    scheduler.add_job(_auto_post_job, "cron", hour=19, minute=0)
    scheduler.start()
    print("CRON: scheduler started — posting at 10:00 AM and 7:00 PM Pacific")

    yield

    scheduler.shutdown()


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
