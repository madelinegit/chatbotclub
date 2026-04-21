"""
Instagram posting service for Maya.
Uses the Instagram Graph API via a Facebook User Access Token
with instagram_basic and instagram_content_publish permissions.

INSTAGRAM_ACCESS_TOKEN env var — NOT the Threads token.
Get one from: developers.facebook.com → Graph API Explorer
Required scopes: instagram_basic, instagram_content_publish, pages_show_list
"""
import requests
from datetime import datetime, timezone, timedelta
from app.config import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID
from app.db.crud import mark_post_posted, mark_post_failed, get_app_token, set_app_token

GRAPH_API = "https://graph.facebook.com/v19.0"
_TOKEN_KEY = "instagram_access_token"
_REFRESH_AFTER_DAYS = 50  # refresh before the 60-day expiry


def get_current_instagram_token() -> str | None:
    """Return the best available Instagram token (DB > env var)."""
    row = get_app_token(_TOKEN_KEY)
    if row and row.get("value"):
        return row["value"]
    return INSTAGRAM_ACCESS_TOKEN


def refresh_instagram_token(token: str = None) -> str | None:
    """
    Exchange a long-lived token for a fresh 60-day token and persist it.
    Uses the provided token or the current best token if omitted.
    Returns the new token string, or None on failure.
    """
    token = token or get_current_instagram_token()
    if not token:
        print("INSTAGRAM REFRESH: no token available to refresh")
        return None
    try:
        r = requests.get(
            "https://graph.facebook.com/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": token},
            timeout=15,
        )
        if not r.ok:
            print(f"INSTAGRAM REFRESH ERROR: {r.status_code} {r.text[:300]}")
            return None
        new_token = r.json().get("access_token")
        if new_token:
            set_app_token(_TOKEN_KEY, new_token)
            print("INSTAGRAM REFRESH: token refreshed and stored in DB")
            return new_token
        print(f"INSTAGRAM REFRESH: unexpected response: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"INSTAGRAM REFRESH EXCEPTION: {e}")
        return None


def maybe_refresh_instagram_token() -> None:
    """Refresh the token if it hasn't been refreshed in _REFRESH_AFTER_DAYS days."""
    row = get_app_token(_TOKEN_KEY)
    if not row:
        return
    updated_at = row.get("updated_at")
    if not updated_at:
        return
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - updated_at).days
    if age_days >= _REFRESH_AFTER_DAYS:
        print(f"INSTAGRAM: token is {age_days} days old — auto-refreshing")
        refresh_instagram_token(row["value"])


def _get_ig_user_id() -> str | None:
    """Get the Instagram Business/Creator Account ID linked to the access token."""
    token = get_current_instagram_token()
    if not token:
        print("INSTAGRAM: no access token available")
        return None
    try:
        r = requests.get(
            f"{GRAPH_API}/me/accounts",
            params={
                "access_token": token,
                "fields": "id,name,access_token,instagram_business_account",
            },
            timeout=10,
        )
        r.raise_for_status()
        pages = r.json().get("data", [])
        print(f"INSTAGRAM: found {len(pages)} pages")
        for page in pages:
            page_name = page.get("name")
            # Try user-token result first
            ig = page.get("instagram_business_account", {})
            if ig.get("id"):
                print(f"INSTAGRAM: page {page_name} ig={ig['id']} (via user token)")
                return ig["id"]

            # Retry using the page's own access token
            page_token = page.get("access_token")
            if page_token:
                r2 = requests.get(
                    f"{GRAPH_API}/{page['id']}",
                    params={
                        "access_token": page_token,
                        "fields": "instagram_business_account",
                    },
                    timeout=10,
                )
                ig2 = r2.json().get("instagram_business_account", {})
                print(f"INSTAGRAM: page {page_name} page-token lookup: {r2.json()}")
                if ig2.get("id"):
                    print(f"INSTAGRAM: page {page_name} ig={ig2['id']} (via page token)")
                    return ig2["id"]
            else:
                print(f"INSTAGRAM: page {page_name} ig=None (no page token returned)")

        print("INSTAGRAM: no Instagram Business/Creator account found on any linked Page")
    except Exception as e:
        print(f"INSTAGRAM USER ID ERROR: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"INSTAGRAM RESPONSE: {e.response.text}")
    return None


def post_carousel_to_instagram(post_id: int, caption: str, image_urls: list, hashtags: str = None) -> bool:
    """
    Publish a carousel (multi-image) post to Instagram.
    image_urls: list of 2–10 publicly accessible image URLs.
    """
    maybe_refresh_instagram_token()
    token = get_current_instagram_token()
    if not token:
        mark_post_failed(post_id)
        return False
    if not image_urls or len(image_urls) < 2:
        print("INSTAGRAM CAROUSEL: need at least 2 images")
        mark_post_failed(post_id)
        return False

    try:
        ig_user_id = INSTAGRAM_USER_ID or _get_ig_user_id()
        if not ig_user_id:
            mark_post_failed(post_id)
            return False

        ig_caption = caption
        if hashtags:
            ig_caption = f"{caption}\n\n{hashtags}"

        # Step 1 — create a container for each image
        child_ids = []
        for url in image_urls[:10]:
            r = requests.post(
                f"{GRAPH_API}/{ig_user_id}/media",
                params={
                    "image_url":     url,
                    "is_carousel_item": "true",
                    "access_token":  token,
                },
                timeout=30,
            )
            r.raise_for_status()
            cid = r.json().get("id")
            if cid:
                child_ids.append(cid)

        if not child_ids:
            print("INSTAGRAM CAROUSEL: no child containers created")
            mark_post_failed(post_id)
            return False

        # Step 2 — create carousel container
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media",
            params={
                "media_type":   "CAROUSEL",
                "caption":      ig_caption,
                "children":     ",".join(child_ids),
                "access_token": token,
            },
            timeout=30,
        )
        r.raise_for_status()
        carousel_id = r.json().get("id")
        if not carousel_id:
            mark_post_failed(post_id)
            return False

        # Step 3 — publish
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media_publish",
            params={"creation_id": carousel_id, "access_token": token},
            timeout=30,
        )
        r.raise_for_status()
        media_id = r.json().get("id")
        mark_post_posted(post_id, str(media_id))
        print(f"INSTAGRAM CAROUSEL: posted {len(child_ids)} images — media id {media_id}")
        return True

    except Exception as e:
        print(f"INSTAGRAM CAROUSEL ERROR: {e}")
        mark_post_failed(post_id)
        return False


def post_reel_to_instagram(post_id: int, caption: str, video_url: str, hashtags: str = None) -> bool:
    """Publish a Reel to Instagram from a video URL (e.g. from Kling)."""
    maybe_refresh_instagram_token()
    token = get_current_instagram_token()
    if not token:
        mark_post_failed(post_id)
        return False
    if not video_url:
        print("INSTAGRAM REEL: no video_url provided")
        mark_post_failed(post_id)
        return False

    try:
        ig_user_id = INSTAGRAM_USER_ID or _get_ig_user_id()
        if not ig_user_id:
            mark_post_failed(post_id)
            return False

        ig_caption = caption
        if hashtags:
            ig_caption = f"{caption}\n\n{hashtags}"

        # Step 1 — create reel container
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media",
            params={
                "media_type":  "REELS",
                "video_url":   video_url,
                "caption":     ig_caption,
                "access_token": token,
            },
            timeout=30,
        )
        r.raise_for_status()
        creation_id = r.json().get("id")
        if not creation_id:
            mark_post_failed(post_id)
            return False

        # Step 2 — wait for video to process then publish
        import time
        for _ in range(12):
            time.sleep(10)
            status_r = requests.get(
                f"{GRAPH_API}/{creation_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=15,
            )
            status = status_r.json().get("status_code")
            print(f"INSTAGRAM REEL: processing status={status}")
            if status == "FINISHED":
                break
            if status == "ERROR":
                mark_post_failed(post_id)
                return False

        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media_publish",
            params={"creation_id": creation_id, "access_token": token},
            timeout=30,
        )
        r.raise_for_status()
        media_id = r.json().get("id")
        mark_post_posted(post_id, str(media_id))
        print(f"INSTAGRAM REEL: posted — media id {media_id}")
        return True

    except Exception as e:
        print(f"INSTAGRAM REEL ERROR: {e}")
        mark_post_failed(post_id)
        return False


def post_to_instagram(post_id: int, caption: str, image_url: str = None, hashtags: str = None) -> tuple[bool, str]:
    """
    Publish a post to Instagram.
    Returns (success, error_message). error_message is empty string on success.
    Instagram Graph API always requires an image — text-only is not supported.
    """
    maybe_refresh_instagram_token()
    token = get_current_instagram_token()
    if not token:
        msg = "No Instagram access token — set INSTAGRAM_ACCESS_TOKEN in Railway env vars"
        print(f"INSTAGRAM: {msg}")
        mark_post_failed(post_id)
        return False, msg

    if not image_url:
        msg = "Instagram requires an image — no image_url on this post"
        print(f"INSTAGRAM: {msg}")
        mark_post_failed(post_id)
        return False, msg

    try:
        ig_user_id = INSTAGRAM_USER_ID or _get_ig_user_id()
        print(f"INSTAGRAM: using ig_user_id={ig_user_id} ({'env var' if INSTAGRAM_USER_ID else 'lookup'})")
        if not ig_user_id:
            msg = "Could not resolve Instagram user ID — set INSTAGRAM_USER_ID in Railway env vars"
            print(f"INSTAGRAM: {msg}")
            mark_post_failed(post_id)
            return False, msg

        ig_caption = caption
        if hashtags:
            ig_caption = f"{caption}\n\n{hashtags}"

        # Step 1 — create media container
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media",
            params={
                "image_url":    image_url,
                "caption":      ig_caption,
                "access_token": token,
            },
            timeout=30,
        )
        if not r.ok:
            msg = f"Instagram media container failed: {r.status_code} {r.text[:300]}"
            print(f"INSTAGRAM ERROR: {msg}")
            mark_post_failed(post_id)
            return False, msg
        creation_id = r.json().get("id")
        if not creation_id:
            msg = f"No creation_id returned: {r.text[:200]}"
            print(f"INSTAGRAM: {msg}")
            mark_post_failed(post_id)
            return False, msg

        # Wait for container to be ready
        import time
        for attempt in range(10):
            time.sleep(3)
            status_r = requests.get(
                f"{GRAPH_API}/{creation_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=15,
            )
            status = status_r.json().get("status_code")
            print(f"INSTAGRAM: container status={status} (attempt {attempt+1})")
            if status == "FINISHED":
                break
            if status == "ERROR":
                msg = f"Container processing error: {status_r.text[:200]}"
                mark_post_failed(post_id)
                return False, msg

        # Step 2 — publish
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media_publish",
            params={"creation_id": creation_id, "access_token": token},
            timeout=30,
        )
        if not r.ok:
            msg = f"Instagram publish failed: {r.status_code} {r.text[:300]}"
            print(f"INSTAGRAM ERROR: {msg}")
            mark_post_failed(post_id)
            return False, msg
        media_id = r.json().get("id")
        mark_post_posted(post_id, str(media_id))
        print(f"INSTAGRAM: posted — media id {media_id}")
        return True, ""

    except Exception as e:
        resp_text = ""
        if hasattr(e, 'response') and e.response is not None:
            resp_text = e.response.text[:300]
        msg = f"{type(e).__name__}: {e} {resp_text}".strip()
        print(f"INSTAGRAM ERROR: {msg}")
        mark_post_failed(post_id)
        return False, msg
