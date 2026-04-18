"""
Instagram OAuth flow.
Visit /auth/instagram to start — redirects to Facebook OAuth.
Facebook redirects back to /auth/instagram/callback with a code.
We exchange the code for a long-lived token and save it to the DB.

Required Railway env vars:
  FB_APP_ID      — App ID from Meta app dashboard (Basic Settings)
  FB_APP_SECRET  — App Secret from Meta app dashboard (Basic Settings)

The redirect URI registered in Meta app (Facebook Login for Business → Settings):
  https://magicmaya.vip/auth/instagram/callback
"""
import os
import requests
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, HTMLResponse

router = APIRouter(prefix="/auth/instagram")

FB_APP_ID     = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI  = "https://magicmaya.vip/auth/instagram/callback"

SCOPES = ",".join([
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
])


@router.get("")
@router.get("/")
def instagram_auth_start():
    """Redirect to Facebook OAuth consent screen."""
    if not FB_APP_ID:
        return HTMLResponse("<h2>FB_APP_ID not set in Railway env vars.</h2>", status_code=500)

    url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={FB_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&response_type=code"
    )
    return RedirectResponse(url)


@router.get("/callback")
def instagram_auth_callback(code: str = Query(None), error: str = Query(None)):
    """Handle OAuth callback, exchange code for token, save to DB."""
    if error:
        return HTMLResponse(f"<h2>OAuth denied: {error}</h2>", status_code=400)
    if not code:
        return HTMLResponse("<h2>No code returned from Facebook.</h2>", status_code=400)

    # Exchange code for short-lived token
    try:
        r = requests.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "client_id":     FB_APP_ID,
                "client_secret": FB_APP_SECRET,
                "redirect_uri":  REDIRECT_URI,
                "code":          code,
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
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type":        "fb_exchange_token",
                "client_id":         FB_APP_ID,
                "client_secret":     FB_APP_SECRET,
                "fb_exchange_token": short_token,
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
    try:
        from app.db.database import get_connection
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO app_tokens (key, value)
            VALUES ('INSTAGRAM_ACCESS_TOKEN', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """, (long_token,))
        conn.commit()
        cur.close()
        conn.close()
        db_saved = True
    except Exception as e:
        db_saved = False
        print(f"TOKEN SAVE ERROR: {e}")

    token_preview = long_token[:20] + "..." if long_token else "none"

    return HTMLResponse(f"""
    <html><body style="font-family:monospace;padding:2rem;background:#111;color:#eee">
    <h2 style="color:#4ade80">Instagram token obtained!</h2>
    <p>Token (first 20 chars): <code>{token_preview}</code></p>
    <p>Expires in: {expires_in} seconds (~60 days)</p>
    <p>Saved to DB: {"yes" if db_saved else "no — save manually"}</p>
    <hr>
    <p>Also add this to Railway env vars as <code>INSTAGRAM_ACCESS_TOKEN</code>:</p>
    <textarea style="width:100%;height:80px;background:#222;color:#fff;padding:8px">{long_token}</textarea>
    <br><br>
    <a href="/admin" style="color:#60a5fa">Back to admin</a>
    </body></html>
    """)
