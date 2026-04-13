from fastapi import APIRouter, Depends, HTTPException
from app.api.chat_routes import get_current_user
from app.db.crud import (
    get_published_blog_posts, get_blog_post_by_slug,
    has_unlocked_blog_post, unlock_blog_post,
    get_credit_balance, deduct_credit, is_dev_user,
)

router = APIRouter(prefix="/api/blog")


@router.get("/posts")
def list_posts(user: dict = Depends(get_current_user)):
    """Return all published posts. Content is withheld for locked posts."""
    posts = get_published_blog_posts()
    user_id = user["user_id"]
    dev = is_dev_user(user_id)
    result = []
    for p in posts:
        is_free = p["credit_cost"] == 0
        unlocked = is_free or dev or has_unlocked_blog_post(user_id, p["id"])
        result.append({
            "id":              p["id"],
            "title":           p["title"],
            "slug":            p["slug"],
            "excerpt":         p["excerpt"],
            "cover_image_url": p["cover_image_url"],
            "credit_cost":     p["credit_cost"],
            "is_free":         is_free,
            "unlocked":        unlocked,
            "published_at":    p["published_at"],
        })
    return {"posts": result}


@router.get("/posts/{slug}")
def get_post(slug: str, user: dict = Depends(get_current_user)):
    """Return a single post. Full content only if free or already unlocked."""
    post = get_blog_post_by_slug(slug)
    if not post or post["status"] != "published":
        raise HTTPException(status_code=404, detail="Post not found.")

    user_id = user["user_id"]
    is_free  = post["credit_cost"] == 0
    unlocked = is_free or is_dev_user(user_id) or has_unlocked_blog_post(user_id, post["id"])

    return {
        "id":              post["id"],
        "title":           post["title"],
        "slug":            post["slug"],
        "excerpt":         post["excerpt"],
        "content":         post["content"] if unlocked else None,
        "cover_image_url": post["cover_image_url"],
        "credit_cost":     post["credit_cost"],
        "is_free":         is_free,
        "unlocked":        unlocked,
        "published_at":    post["published_at"],
    }


@router.post("/posts/{slug}/unlock")
def unlock_post(slug: str, user: dict = Depends(get_current_user)):
    """Spend credits to unlock a post. Idempotent — won't double-charge."""
    post = get_blog_post_by_slug(slug)
    if not post or post["status"] != "published":
        raise HTTPException(status_code=404, detail="Post not found.")

    if post["credit_cost"] == 0:
        return {"unlocked": True, "credits_spent": 0}

    user_id = user["user_id"]

    if has_unlocked_blog_post(user_id, post["id"]):
        return {"unlocked": True, "credits_spent": 0}

    cost = post["credit_cost"]
    dev = is_dev_user(user_id)
    if not dev and get_credit_balance(user_id) < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Not enough credits. This post costs {cost} credit{'s' if cost != 1 else ''}."
        )

    if not dev:
        for _ in range(cost):
            deduct_credit(user_id)

    unlock_blog_post(user_id, post["id"])
    return {"unlocked": True, "credits_spent": cost}
