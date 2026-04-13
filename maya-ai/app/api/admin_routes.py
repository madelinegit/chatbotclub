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
    from app.db.database import get_connection
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM social_posts WHERE id = ?", (post_id,)
    ).fetchone()
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
    from app.db.database import get_connection
    conn = get_connection()

    pending_posts = conn.execute(
        "SELECT COUNT(*) FROM social_posts WHERE status='pending'"
    ).fetchone()[0]

    posted_today = conn.execute(
        "SELECT COUNT(*) FROM social_posts WHERE status='posted' AND date(posted_at)=date('now')"
    ).fetchone()[0]

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    messages_today = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE date(created_at)=date('now') AND role='user'"
    ).fetchone()[0]

    conn.close()
    return {
        "pending_posts":  pending_posts,
        "posted_today":   posted_today,
        "total_users":    total_users,
        "messages_today": messages_today,
    }


# ── Users API ─────────────────────────────────────────────────────────────────

@router.post("/users/{user_id}/set-dev")
def set_dev(user_id: str, secret: str = Query(...), enabled: bool = Query(True)):
    _check(secret)
    from app.db.crud import set_dev_user, get_user_by_id
    if not get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    set_dev_user(user_id, enabled)
    return {"user_id": user_id, "is_dev": enabled}


@router.get("/users")
def list_users(secret: str = Query(...)):
    _check(secret)
    from app.db.database import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT u.id, u.email, u.created_at, u.age_verified, u.is_dev,
               COALESCE(c.balance, 0) as credits,
               (SELECT COUNT(*) FROM messages m WHERE m.user_id = u.id AND m.role='user') as message_count
        FROM users u
        LEFT JOIN credits c ON c.user_id = u.id
        ORDER BY u.created_at DESC
    """).fetchall()
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
