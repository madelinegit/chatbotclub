"""
Social engagement service for Maya.
- Fetches comments/replies on Maya's Threads posts
- Generates replies in Maya's voice using the LLM
- Posts the replies back to Threads
- Can also post outbound comments on any Threads post by ID
"""
import requests
from app.config import (
    THREADS_ACCESS_TOKEN,
    MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL,
)
from app.ai.persona import load_persona
from app.db.crud import (
    log_comment_reply, has_replied_to_comment, get_recent_comment_replies,
)

THREADS_API = "https://graph.threads.net/v1.0"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_user_id() -> str | None:
    try:
        r = requests.get(
            f"{THREADS_API}/me",
            params={"fields": "id,username", "access_token": THREADS_ACCESS_TOKEN},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("id")
    except Exception as e:
        print(f"ENGAGEMENT USER ID ERROR: {e}")
        return None


def _llm_reply(comment_text: str, post_caption: str = "") -> str | None:
    """Call the LLM to write a reply in Maya's voice."""
    persona = load_persona()
    prompt  = (
        f"Someone replied to one of your Threads posts. Write a short, authentic reply as Maya.\n\n"
        f"Your original post: {post_caption or '(one of your posts)'}\n"
        f"Their comment: {comment_text}\n\n"
        "Reply as Maya — real, direct, 1-2 sentences max. Lowercase is fine. No hashtags. "
        "Just the reply text, nothing else."
    )
    payload = {
        "model":    MODELSLAB_MODEL,
        "messages": [
            {"role": "system", "content": persona},
            {"role": "user",   "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {MODELSLAB_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        r = requests.post(MODELSLAB_API_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        if "output" in data:
            return data["output"][0].strip().strip('"').strip("'")
    except Exception as e:
        print(f"ENGAGEMENT LLM ERROR: {e}")
    return None


def _llm_comment(topic: str = "") -> str | None:
    """Generate a short outbound comment Maya would drop on someone's post."""
    persona = load_persona()
    context = f"The post is about: {topic}" if topic else "You're browsing Threads and want to drop a comment."
    prompt  = (
        f"{context}\n\n"
        "Write a short, real comment Maya would leave — 1 sentence, casual, no hashtags, "
        "no emojis unless it genuinely fits. Just the comment text."
    )
    payload = {
        "model":    MODELSLAB_MODEL,
        "messages": [
            {"role": "system", "content": persona},
            {"role": "user",   "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {MODELSLAB_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        r = requests.post(MODELSLAB_API_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        if "output" in data:
            return data["output"][0].strip().strip('"').strip("'")
    except Exception as e:
        print(f"ENGAGEMENT LLM ERROR: {e}")
    return None


def _post_reply(reply_to_id: str, text: str) -> str | None:
    """
    Post a reply to a Threads post/comment.
    reply_to_id can be a top-level thread ID or a reply ID.
    Returns the new thread ID or None on failure.
    """
    user_id = _get_user_id()
    if not user_id:
        return None
    try:
        # Step 1 — create reply container
        r = requests.post(
            f"{THREADS_API}/{user_id}/threads",
            params={
                "media_type":   "TEXT",
                "text":         text,
                "reply_to_id":  reply_to_id,
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=30,
        )
        r.raise_for_status()
        creation_id = r.json().get("id")
        if not creation_id:
            return None

        # Step 2 — publish
        r = requests.post(
            f"{THREADS_API}/{user_id}/threads_publish",
            params={"creation_id": creation_id, "access_token": THREADS_ACCESS_TOKEN},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("id")
    except Exception as e:
        print(f"ENGAGEMENT REPLY POST ERROR: {e}")
        return None


SEARCH_KEYWORDS = [
    "lake tahoe", "squaw valley", "snowboarding", "powder day",
    "yoga", "tahoe", "burning man", "ski tahoe",
]


def _search_threads(keyword: str, limit: int = 10) -> list:
    """Search public Threads posts by keyword."""
    try:
        r = requests.get(
            f"{THREADS_API}/threads/search",
            params={
                "q":            keyword,
                "fields":       "id,text,username,timestamp",
                "limit":        limit,
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        print(f"ENGAGEMENT SEARCH ERROR ({keyword}): {e}")
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_my_threads(limit: int = 20) -> list:
    """Return Maya's recent Threads posts [{id, text, timestamp}, ...]."""
    user_id = _get_user_id()
    if not user_id:
        return []
    try:
        r = requests.get(
            f"{THREADS_API}/{user_id}/threads",
            params={
                "fields":       "id,text,timestamp",
                "limit":        limit,
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        print(f"ENGAGEMENT FETCH POSTS ERROR: {e}")
        return []


def fetch_comments_on_post(thread_id: str) -> list:
    """Return replies on a single Threads post [{id, text, username, timestamp}, ...]."""
    try:
        r = requests.get(
            f"{THREADS_API}/{thread_id}/replies",
            params={
                "fields":       "id,text,username,timestamp",
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        print(f"ENGAGEMENT FETCH COMMENTS ERROR: {e}")
        return []


def fetch_pending_comments() -> list:
    """
    Collect all unanswered comments on Maya's recent posts.
    Returns a list of dicts with post and comment details.
    """
    pending = []
    posts   = fetch_my_threads(limit=20)
    for post in posts:
        comments = fetch_comments_on_post(post["id"])
        for comment in comments:
            if not comment.get("text"):
                continue
            if has_replied_to_comment("threads", comment["id"]):
                continue
            pending.append({
                "post_id":      post["id"],
                "post_caption": post.get("text", ""),
                "comment_id":   comment["id"],
                "comment_text": comment.get("text", ""),
                "username":     comment.get("username", ""),
                "timestamp":    comment.get("timestamp", ""),
            })
    return pending


def reply_to_comment(comment_id: str, post_id: str, post_caption: str,
                     comment_text: str, reply_text: str = None) -> dict:
    """
    Reply to a specific comment.
    If reply_text is None, generates one via the LLM.
    Returns {ok: bool, reply: str, platform_id: str}
    """
    if not reply_text:
        reply_text = _llm_reply(comment_text, post_caption)
    if not reply_text:
        return {"ok": False, "error": "LLM generation failed"}

    platform_id = _post_reply(comment_id, reply_text)
    if not platform_id:
        return {"ok": False, "reply": reply_text, "error": "Threads API post failed"}

    log_comment_reply(
        platform="threads",
        comment_id=comment_id,
        post_id=post_id,
        reply_text=reply_text,
        platform_reply_id=platform_id,
    )
    print(f"ENGAGEMENT: replied to comment {comment_id} — {reply_text[:60]}")
    return {"ok": True, "reply": reply_text, "platform_id": platform_id}


def run_engagement_pass() -> dict:
    """
    Auto-reply to all unanswered comments on Maya's recent posts.
    Returns {replied, skipped, errors}.
    """
    if not THREADS_ACCESS_TOKEN:
        return {"error": "THREADS_ACCESS_TOKEN not set"}

    replied = 0
    skipped = 0
    errors  = 0

    pending = fetch_pending_comments()
    for item in pending:
        result = reply_to_comment(
            comment_id=item["comment_id"],
            post_id=item["post_id"],
            post_caption=item["post_caption"],
            comment_text=item["comment_text"],
        )
        if result.get("ok"):
            replied += 1
        elif "LLM" in result.get("error", "") or "API" in result.get("error", ""):
            errors += 1
        else:
            skipped += 1

    return {"replied": replied, "skipped": skipped, "errors": errors}


def post_outbound_comment(thread_id: str, topic: str = "", custom_text: str = "") -> dict:
    """
    Have Maya comment on any public Threads post by its ID.
    Provide custom_text to skip LLM generation, or topic for context.
    Returns {ok: bool, reply: str, platform_id: str}
    """
    if not THREADS_ACCESS_TOKEN:
        return {"ok": False, "error": "THREADS_ACCESS_TOKEN not set"}

    text = custom_text or _llm_comment(topic)
    if not text:
        return {"ok": False, "error": "Could not generate comment"}

    platform_id = _post_reply(thread_id, text)
    if not platform_id:
        return {"ok": False, "text": text, "error": "Threads API post failed"}

    log_comment_reply(
        platform="threads",
        comment_id=thread_id,
        post_id=thread_id,
        reply_text=text,
        platform_reply_id=platform_id,
    )
    print(f"ENGAGEMENT OUTBOUND: commented on {thread_id} — {text[:60]}")
    return {"ok": True, "text": text, "platform_id": platform_id}


def find_posts_to_comment(max_results: int = 10) -> list:
    """
    Search Threads for posts matching Maya's interests.
    Returns a list of posts Maya hasn't already commented on.
    """
    if not THREADS_ACCESS_TOKEN:
        return []

    import random
    keywords = random.sample(SEARCH_KEYWORDS, min(3, len(SEARCH_KEYWORDS)))
    seen_ids = set()
    candidates = []

    for kw in keywords:
        posts = _search_threads(kw, limit=10)
        for post in posts:
            pid = post.get("id")
            if not pid or pid in seen_ids:
                continue
            if has_replied_to_comment("threads", pid):
                continue
            seen_ids.add(pid)
            candidates.append({
                "post_id":   pid,
                "text":      post.get("text", ""),
                "username":  post.get("username", ""),
                "keyword":   kw,
                "timestamp": post.get("timestamp", ""),
            })

    return candidates[:max_results]


def preview_outbound_comments(max_results: int = 6) -> list:
    """
    Find posts and generate draft comments for each — returns list for review before posting.
    """
    posts = find_posts_to_comment(max_results=max_results)
    previews = []
    for post in posts:
        topic   = post.get("text", "")[:120]
        comment = _llm_comment(topic)
        if comment:
            previews.append({**post, "draft_comment": comment})
    return previews
