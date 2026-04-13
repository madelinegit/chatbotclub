from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI(title="Maya AI")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@app.get("/debug")
def debug(request: Request):
    return JSONResponse({
        "url": str(request.url),
        "base_url": str(request.base_url),
        "headers": dict(request.headers),
        "scheme": request.url.scheme,
    })


@app.get("/", response_class=HTMLResponse)
def landing_page():
    return HTMLResponse("""<!DOCTYPE html>
<html><head><title>Maya</title></head>
<body style="background:#0a0a0b;color:#f0ede8;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
  <h1 style="font-size:4rem;color:#e8c8a0;margin:0">Maya</h1>
  <p style="color:#9b9790;margin-top:16px">She's waiting.</p>
  <a href="/register" style="display:inline-block;margin-top:24px;background:#c9956a;color:#0a0a0b;padding:14px 36px;border-radius:999px;text-decoration:none;font-weight:700">Meet Maya</a>
</div>
</body></html>""")


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
