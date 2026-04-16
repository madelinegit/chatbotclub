"""
Instagram posting service for Maya.
Uses the Instagram Graph API via the same Meta credentials as Threads.
Requires an Instagram Business or Creator account connected to a Facebook Page.
"""
import requests
from app.config import THREADS_ACCESS_TOKEN
from app.db.crud import mark_post_posted, mark_post_failed

GRAPH_API = "https://graph.facebook.com/v19.0"


def _get_ig_user_id() -> str | None:
    """Get the Instagram Business Account ID linked to the access token."""
    try:
        r = requests.get(
            f"{GRAPH_API}/me/accounts",
            params={"access_token": THREADS_ACCESS_TOKEN, "fields": "instagram_business_account"},
            timeout=10,
        )
        r.raise_for_status()
        pages = r.json().get("data", [])
        for page in pages:
            ig = page.get("instagram_business_account", {})
            if ig.get("id"):
                return ig["id"]
    except Exception as e:
        print(f"INSTAGRAM USER ID ERROR: {e}")
    return None


def post_to_instagram(post_id: int, caption: str, image_url: str = None) -> bool:
    """
    Publish a post to Instagram.
    Images: create container then publish.
    Text-only: not supported by Instagram Graph API — requires an image.
    """
    if not THREADS_ACCESS_TOKEN:
        print("INSTAGRAM: no access token set")
        return False

    if not image_url:
        print("INSTAGRAM: skipping — Instagram requires an image, no image_url provided")
        mark_post_failed(post_id)
        return False

    try:
        ig_user_id = _get_ig_user_id()
        if not ig_user_id:
            print("INSTAGRAM: could not get IG user ID — is the account a Business/Creator account connected to a Page?")
            mark_post_failed(post_id)
            return False

        # Step 1 — create media container
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media",
            params={
                "image_url":    image_url,
                "caption":      caption,
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=30,
        )
        r.raise_for_status()
        creation_id = r.json().get("id")
        if not creation_id:
            print("INSTAGRAM: no creation_id returned")
            mark_post_failed(post_id)
            return False

        # Step 2 — publish
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media_publish",
            params={"creation_id": creation_id, "access_token": THREADS_ACCESS_TOKEN},
            timeout=30,
        )
        r.raise_for_status()
        media_id = r.json().get("id")
        mark_post_posted(post_id, str(media_id))
        print(f"INSTAGRAM: posted — media id {media_id}")
        return True

    except Exception as e:
        print(f"INSTAGRAM ERROR: {e}")
        mark_post_failed(post_id)
        return False
