"""
Threads OAuth flow — generates a fresh long-lived access token.
Visit /auth/threads to start.

Required Railway env vars (same as Instagram — already set):
  FB_APP_ID      — App ID from Meta app dashboard
  FB_APP_SECRET  — App Secret from Meta app dashboard

Add this redirect URI in Meta app → Use Cases → Threads API → Settings:
  https://magicmaya.vip/auth/threads/callback
"""
import os
import requests
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, HTMLResponse

router = APIRouter(prefix="/auth/threads")

FB_APP_ID     = os.getenv("THREADS_APP_ID") or os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("THREADS_APP_SECRET") or os.getenv("FB_APP_SECRET")
REDIRECT_URI  = "https://magicmaya.vip/auth/threads/callback"

SCOPES = ",".join([
    "threads_basic",
    "threads_content_publish",
    "threads_manage_replies",
    "threads_keyword_search",
])


@router.get("")
@router.get("/")
def threads_auth_start():
    if not FB_APP_ID:
        return HTMLResponse("<h2>FB_APP_ID not set in Railway env vars.</h2>", status_code=500)
    url = (
        f"https://threads.net/oauth/authorize"
        f"?client_id={FB_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&response_type=code"
    )
    return RedirectResponse(url)


@router.get("/callback")
def threads_auth_callback(code: str = Query(None), error: str = Query(None)):
    if error:
        return HTMLResponse(f"<h2>OAuth denied: {error}</h2>", status_code=400)
    if not code:
        return HTMLResponse("<h2>No code returned from Threads.</h2>", status_code=400)

    # Exchange code for short-lived token
    try:
        r = requests.post(
            "https://graph.threads.net/oauth/access_token",
            data={
                "client_id":     FB_APP_ID,
                "client_secret": FB_APP_SECRET,
                "redirect_uri":  REDIRECT_URI,
                "code":          code,
                "grant_type":    "authorization_code",
            },
            timeout=15,
        )
        r.raise_for_status()
        short_token = r.json().get("access_token")
        if not short_token:
            return HTMLResponse(f"<h2>Token exchange failed: {r.text}</h2>", status_code=500)
    except Exception as e:
        return HTMLResponse(f"<h2>Token exchange error: {e}</h2>", status_code=500)

    # Exchange for long-lived token (60 days)
    try:
        r2 = requests.get(
            "https://graph.threads.net/access_token",
            params={
                "grant_type":    "th_exchange_token",
                "client_secret": FB_APP_SECRET,
                "access_token":  short_token,
            },
            timeout=15,
        )
        r2.raise_for_status()
        long_token = r2.json().get("access_token")
        expires_in = r2.json().get("expires_in", "unknown")
    except Exception as e:
        long_token = short_token
        expires_in = "short-lived only"

    # Save to DB
    db_saved = False
    try:
        from app.db.database import get_connection
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO app_tokens (key, value)
            VALUES ('THREADS_ACCESS_TOKEN', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """, (long_token,))
        conn.commit()
        cur.close()
        conn.close()
        db_saved = True
    except Exception as e:
        print(f"THREADS TOKEN SAVE ERROR: {e}")

    token_preview = long_token[:20] + "..." if long_token else "none"

    return HTMLResponse(f"""
    <html><body style="font-family:monospace;padding:2rem;background:#111;color:#eee">
    <h2 style="color:#4ade80">Threads token obtained!</h2>
    <p>Token preview: <code>{token_preview}</code></p>
    <p>Expires in: {expires_in} seconds (~60 days)</p>
    <p>Saved to DB: {"yes ✓" if db_saved else "no — save manually"}</p>
    <hr>
    <p><strong>Copy this into Railway as <code>THREADS_ACCESS_TOKEN</code>:</strong></p>
    <textarea style="width:100%;height:80px;background:#222;color:#4ade80;padding:8px;font-size:13px">{long_token}</textarea>
    <br><br>
    <a href="/admin" style="color:#60a5fa">Back to admin</a>
    </body></html>
    """)
