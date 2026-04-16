"""
Threads posting service for Maya.
Uses the Threads API to publish text and image posts as magicmayavip.
"""
import requests
from app.config import THREADS_ACCESS_TOKEN
from app.db.crud import mark_post_posted, mark_post_failed

THREADS_API = "https://graph.threads.net/v1.0"


def _get_user_id() -> str | None:
    """Fetch the Threads user ID for the authenticated account."""
    try:
        r = requests.get(
            f"{THREADS_API}/me",
            params={"fields": "id,username", "access_token": THREADS_ACCESS_TOKEN},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("id")
    except Exception as e:
        print(f"THREADS USER ID ERROR: {e}")
        return None


def post_to_threads(post_id: int, caption: str, image_url: str = None) -> bool:
    """
    Publish a post to Threads.
    Text-only posts publish immediately.
    Image posts create a container then publish.
    """
    if not THREADS_ACCESS_TOKEN:
        print("THREADS: no access token set")
        return False

    try:
        user_id = _get_user_id()
        if not user_id:
            mark_post_failed(post_id)
            return False

        # Step 1 — create media container
        if image_url:
            container_params = {
                "media_type":   "IMAGE",
                "image_url":    image_url,
                "text":         caption,
                "access_token": THREADS_ACCESS_TOKEN,
            }
        else:
            container_params = {
                "media_type":   "TEXT",
                "text":         caption,
                "access_token": THREADS_ACCESS_TOKEN,
            }

        r = requests.post(
            f"{THREADS_API}/{user_id}/threads",
            params=container_params,
            timeout=30,
        )
        r.raise_for_status()
        creation_id = r.json().get("id")
        if not creation_id:
            print("THREADS: no creation_id returned")
            mark_post_failed(post_id)
            return False

        # Step 2 — publish the container
        r = requests.post(
            f"{THREADS_API}/{user_id}/threads_publish",
            params={"creation_id": creation_id, "access_token": THREADS_ACCESS_TOKEN},
            timeout=30,
        )
        r.raise_for_status()
        thread_id = r.json().get("id")
        mark_post_posted(post_id, str(thread_id))
        print(f"THREADS: posted — thread id {thread_id}")
        return True

    except Exception as e:
        print(f"THREADS ERROR: {e}")
        mark_post_failed(post_id)
        return False
