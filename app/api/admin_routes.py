"""
Admin routes — protected by ADMIN_SECRET env var.
Access at /admin (login page) then /admin/dashboard
"""
import os
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import re
from app.db.crud import (
    get_pending_posts, get_all_posts,
    approve_post, reject_post,
    get_all_blog_posts, get_blog_post_by_id,
    create_blog_post, update_blog_post,
    publish_blog_post, unpublish_blog_post, delete_blog_post,
)
from app.services.social_service import post_to_x

router       = APIRouter(prefix="/admin")
templates    = Jinja2Templates(directory="templates")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me-admin")


def _check(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden.")


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse(request, "admin_login.html", {})


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, secret: str = Query(...)):
    _check(secret)
    return templates.TemplateResponse(request, "admin_dashboard.html", {"secret": secret})


# ── Posts API ─────────────────────────────────────────────────────────────────

@router.get("/posts")
def list_posts(secret: str = Query(...), status: str = Query("pending")):
    _check(secret)
    if status == "all":
        return {"posts": get_all_posts()}
    return {"posts": get_pending_posts()}


@router.post("/posts/{post_id}/approve")
def approve(post_id: int, secret: str = Query(...)):
    _check(secret)
    approve_post(post_id)
    return {"status": "approved"}


@router.post("/posts/{post_id}/reject")
def reject(post_id: int, secret: str = Query(...)):
    _check(secret)
    reject_post(post_id)
    return {"status": "rejected"}


@router.post("/posts/{post_id}/post-now")
def post_now(post_id: int, secret: str = Query(...)):
    _check(secret)
    import psycopg2.extras
    from app.db.database import get_connection
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM social_posts WHERE id = %s", (post_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Post not found.")

    approve_post(post_id)
    success = post_to_x(
        post_id=post_id,
        caption=row["caption"],
        image_url=row["image_url"],
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to post to X.")
    return {"status": "posted"}


@router.post("/generate")
def generate_post_now(secret: str = Query(...)):
    _check(secret)
    from app.services.social_service import generate_post_for_queue
    from app.services.local_context_service import get_local_context
    context = get_local_context()
    result  = generate_post_for_queue(local_context=context)
    if not result:
        raise HTTPException(status_code=500, detail="Generation failed.")
    return result


# ── Stats API ─────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(secret: str = Query(...)):
    _check(secret)
    import psycopg2.extras
    from app.db.database import get_connection
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM social_posts WHERE status='pending'")
    pending_posts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM social_posts WHERE status='posted' AND posted_at::date = CURRENT_DATE")
    posted_today = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM messages WHERE created_at::date = CURRENT_DATE AND role='user'")
    messages_today = cur.fetchone()[0]

    cur.close()
    conn.close()
    return {
        "pending_posts":  pending_posts,
        "posted_today":   posted_today,
        "total_users":    total_users,
        "messages_today": messages_today,
    }


# ── Users API ─────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(secret: str = Query(...)):
    _check(secret)
    import psycopg2.extras
    from app.db.database import get_connection
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.id, u.email, u.created_at, u.age_verified, u.is_dev,
               COALESCE(c.balance, 0) as credits,
               (SELECT COUNT(*) FROM messages m WHERE m.user_id = u.id AND m.role='user') as message_count
        FROM users u
        LEFT JOIN credits c ON c.user_id = u.id
        ORDER BY u.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"users": [dict(r) for r in rows]}


# ── Blog Admin API ────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


@router.get("/blog/posts")
def admin_list_blog_posts(secret: str = Query(...)):
    _check(secret)
    return {"posts": get_all_blog_posts()}


@router.post("/blog/posts")
async def admin_create_blog_post(secret: str = Query(...), request: Request = None):
    _check(secret)
    body = await request.json()
    title            = body.get("title", "").strip()
    slug             = body.get("slug", "").strip() or _slugify(title)
    excerpt          = body.get("excerpt", "").strip()
    content          = body.get("content", "").strip()
    cover_image_url  = body.get("cover_image_url", "").strip() or None
    credit_cost      = int(body.get("credit_cost", 5))

    if not title or not excerpt or not content:
        raise HTTPException(status_code=400, detail="title, excerpt, and content are required.")
    if not slug:
        raise HTTPException(status_code=400, detail="Could not generate slug from title.")

    try:
        post_id = create_blog_post(title, slug, excerpt, content, cover_image_url, credit_cost)
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail=f"Slug '{slug}' is already taken.")
        raise HTTPException(status_code=500, detail=str(e))

    return {"id": post_id, "slug": slug}


@router.put("/blog/posts/{post_id}")
async def admin_update_blog_post(post_id: int, secret: str = Query(...), request: Request = None):
    _check(secret)
    if not get_blog_post_by_id(post_id):
        raise HTTPException(status_code=404, detail="Post not found.")
    body = await request.json()
    update_blog_post(
        post_id,
        title           = body.get("title"),
        slug            = body.get("slug"),
        excerpt         = body.get("excerpt"),
        content         = body.get("content"),
        cover_image_url = body.get("cover_image_url"),
        credit_cost     = body.get("credit_cost"),
    )
    return {"status": "updated"}


@router.post("/blog/posts/{post_id}/publish")
def admin_publish_blog_post(post_id: int, secret: str = Query(...)):
    _check(secret)
    if not get_blog_post_by_id(post_id):
        raise HTTPException(status_code=404, detail="Post not found.")
    publish_blog_post(post_id)
    return {"status": "published"}


@router.post("/blog/posts/{post_id}/unpublish")
def admin_unpublish_blog_post(post_id: int, secret: str = Query(...)):
    _check(secret)
    if not get_blog_post_by_id(post_id):
        raise HTTPException(status_code=404, detail="Post not found.")
    unpublish_blog_post(post_id)
    return {"status": "draft"}


@router.delete("/blog/posts/{post_id}")
def admin_delete_blog_post(post_id: int, secret: str = Query(...)):
    _check(secret)
    if not get_blog_post_by_id(post_id):
        raise HTTPException(status_code=404, detail="Post not found.")
    delete_blog_post(post_id)
    return {"status": "deleted"}


# ── Local Context API ─────────────────────────────────────────────────────────

@router.get("/local-context")
def local_context_preview(secret: str = Query(...)):
    _check(secret)
    from app.services.local_context_service import get_local_context
    context = get_local_context()
    return {"context": context or "Nothing fetched — check RSS feeds or network."}
