"""
Instagram posting service for Maya.
Uses the Instagram Graph API via a Facebook User Access Token
with instagram_basic and instagram_content_publish permissions.

INSTAGRAM_ACCESS_TOKEN env var — NOT the Threads token.
Get one from: developers.facebook.com → Graph API Explorer
Required scopes: instagram_basic, instagram_content_publish, pages_show_list
"""
import requests
from app.config import INSTAGRAM_ACCESS_TOKEN
from app.db.crud import mark_post_posted, mark_post_failed

GRAPH_API = "https://graph.facebook.com/v19.0"


def _get_ig_user_id() -> str | None:
    """Get the Instagram Business/Creator Account ID linked to the access token."""
    if not INSTAGRAM_ACCESS_TOKEN:
        print("INSTAGRAM: INSTAGRAM_ACCESS_TOKEN env var not set")
        return None
    try:
        r = requests.get(
            f"{GRAPH_API}/me/accounts",
            params={
                "access_token": INSTAGRAM_ACCESS_TOKEN,
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


def post_to_instagram(post_id: int, caption: str, image_url: str = None) -> bool:
    """
    Publish a post to Instagram.
    Instagram Graph API always requires an image — text-only is not supported.
    """
    if not INSTAGRAM_ACCESS_TOKEN:
        print("INSTAGRAM: INSTAGRAM_ACCESS_TOKEN not set — add it to Railway env vars")
        mark_post_failed(post_id)
        return False

    if not image_url:
        print("INSTAGRAM: skipping — Instagram requires an image, no image_url provided")
        mark_post_failed(post_id)
        return False

    try:
        ig_user_id = _get_ig_user_id()
        if not ig_user_id:
            print("INSTAGRAM: could not resolve IG user ID — check token permissions")
            mark_post_failed(post_id)
            return False

        # Step 1 — create media container
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media",
            params={
                "image_url":    image_url,
                "caption":      caption,
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=30,
        )
        r.raise_for_status()
        creation_id = r.json().get("id")
        if not creation_id:
            print(f"INSTAGRAM: no creation_id returned — {r.text}")
            mark_post_failed(post_id)
            return False

        # Step 2 — publish
        r = requests.post(
            f"{GRAPH_API}/{ig_user_id}/media_publish",
            params={"creation_id": creation_id, "access_token": INSTAGRAM_ACCESS_TOKEN},
            timeout=30,
        )
        r.raise_for_status()
        media_id = r.json().get("id")
        mark_post_posted(post_id, str(media_id))
        print(f"INSTAGRAM: posted — media id {media_id}")
        return True

    except Exception as e:
        print(f"INSTAGRAM ERROR: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"INSTAGRAM RESPONSE: {e.response.text}")
        mark_post_failed(post_id)
        return False
