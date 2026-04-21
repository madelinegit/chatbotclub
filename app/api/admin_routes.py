"""
Admin routes — protected by ADMIN_SECRET env var.
Access at /admin (login page) then /admin/dashboard
"""
import os
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import re
from app.db.crud import (
    get_pending_posts, get_all_posts, get_posted_posts,
    approve_post, reject_post,
    update_social_post, delete_social_post, retry_social_post,
    get_all_blog_posts, get_blog_post_by_id,
    create_blog_post, update_blog_post,
    publish_blog_post, unpublish_blog_post, delete_blog_post,
)
from app.services.threads_service import post_to_threads

router       = APIRouter(prefix="/admin")
templates    = Jinja2Templates(directory="templates")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me-admin")


def _check(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden.")


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
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
    if status == "posted":
        return {"posts": get_posted_posts()}
    return {"posts": get_pending_posts()}


@router.put("/posts/{post_id}")
async def edit_post(post_id: int, secret: str = Query(...), request: Request = None):
    _check(secret)
    body         = await request.json()
    caption      = body.get("caption")
    image_url    = body.get("image_url")
    clear_image  = body.get("clear_image", False)
    scheduled_at = body.get("scheduled_at") or None
    update_social_post(post_id, caption=caption, image_url=image_url, clear_image=clear_image, scheduled_at=scheduled_at)
    return {"status": "updated"}


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


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, secret: str = Query(...)):
    _check(secret)
    delete_social_post(post_id)
    return {"status": "deleted"}


@router.post("/posts/{post_id}/retry")
def retry_post(post_id: int, secret: str = Query(...)):
    _check(secret)
    retry_social_post(post_id)
    return {"status": "pending"}


@router.post("/posts/{post_id}/duplicate")
def duplicate_post(post_id: int, secret: str = Query(...)):
    _check(secret)
    import psycopg2.extras
    from app.db.database import get_connection
    from app.db.crud import create_social_post
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM social_posts WHERE id = %s", (post_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Post not found.")
    new_id = create_social_post(
        caption=row["caption"],
        image_url=row.get("image_url"),
        image_prompt=row.get("image_prompt"),
        hashtags=row.get("hashtags"),
        target_platform=row.get("target_platform", "threads"),
    )
    return {"id": new_id, "status": "pending"}


@router.post("/posts/{post_id}/post-now")
def post_now(post_id: int, secret: str = Query(...), platform: str = Query("threads")):
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

    # Record which platform we're actually posting to
    conn2 = get_connection()
    cur2  = conn2.cursor()
    cur2.execute("UPDATE social_posts SET target_platform = %s WHERE id = %s", (platform, post_id))
    conn2.commit()
    cur2.close()
    conn2.close()

    approve_post(post_id)

    err_msg = ""
    if platform == "instagram":
        from app.services.instagram_service import post_to_instagram
        success, err_msg = post_to_instagram(
            post_id=post_id,
            caption=row["caption"],
            image_url=row["image_url"],
            hashtags=row.get("hashtags"),
        )
    elif platform == "x":
        from app.services.social_service import post_to_x
        success = post_to_x(
            post_id=post_id,
            caption=row["caption"],
            image_url=row["image_url"],
        )
    else:
        success = post_to_threads(
            post_id=post_id,
            caption=row["caption"],
            image_url=row["image_url"],
        )

    if not success:
        detail = err_msg or f"Failed to post to {platform} — check Railway logs."
        raise HTTPException(status_code=500, detail=detail)
    return {"status": "posted", "platform": platform}


@router.post("/posts/{post_id}/archive")
def archive_post(post_id: int, secret: str = Query(...)):
    _check(secret)
    from app.db.crud import archive_social_post
    archive_social_post(post_id)
    return {"status": "archived"}


@router.post("/upload-image")
async def upload_image(secret: str = Query(...), file: UploadFile = File(...)):
    """Upload an image file to Cloudinary and return the public URL."""
    _check(secret)
    from app.config import CLOUDINARY_URL
    if not CLOUDINARY_URL:
        raise HTTPException(status_code=422, detail="CLOUDINARY_URL not set in Railway env vars.")
    try:
        import base64
        contents = await file.read()
        mime = file.content_type or "image/jpeg"
        encoded = base64.b64encode(contents).decode("utf-8")
        data_uri = f"data:{mime};base64,{encoded}"

        stripped = CLOUDINARY_URL.replace("cloudinary://", "")
        auth_part, cloud_name = stripped.rsplit("@", 1)
        api_key, api_secret = auth_part.split(":", 1)

        import requests as req
        r = req.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            data={"file": data_uri, "upload_preset": "ml_default"},
            auth=(api_key, api_secret),
            timeout=30,
        )
        r.raise_for_status()
        url = r.json().get("secure_url")
        if not url:
            raise HTTPException(status_code=500, detail=f"Cloudinary returned no URL: {r.text}")
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {e}")


@router.post("/generate-img2img")
async def generate_img2img(secret: str = Query(...), request: Request = None):
    """
    Insert Maya into a scene via Flux LoRA img2img.
    Body: { image_url, prompt, prompt_strength (0.5-0.95) }
    """
    _check(secret)
    body            = await request.json()
    image_url       = body.get("image_url", "").strip()
    prompt          = body.get("prompt", "").strip()
    prompt_strength = float(body.get("prompt_strength", 0.8))
    character       = body.get("character", "mayaleja")
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url required.")
    from app.services.social_service import _generate_image_lora
    url, err = _generate_image_lora(prompt or "in the scene, natural pose", image_url=image_url, prompt_strength=prompt_strength, character=character)
    if err:
        raise HTTPException(status_code=500, detail=err)
    return {"image_url": url}


@router.post("/write/chat")
async def admin_write_chat(secret: str = Query(...), request: Request = None):
    """Chat with Maya in admin — she writes back in her voice."""
    _check(secret)
    body    = await request.json()
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required.")

    import requests as req
    from app.config import MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL
    from app.ai.persona import load_persona

    persona = load_persona()
    system  = persona + (
        "\n\nYou are chatting with your admin (the person who runs your account). "
        "They may ask you to write posts, captions, ideas, or just talk. "
        "Stay in character as Maya. Be real, direct, conversational."
    )

    payload = {
        "model":    MODELSLAB_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": message},
        ],
    }
    headers = {
        "Authorization": f"Bearer {MODELSLAB_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        r = req.post(MODELSLAB_API_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data  = r.json()
        reply = ""
        if "choices" in data:
            reply = data["choices"][0]["message"]["content"].strip()
        elif "output" in data:
            reply = data["output"][0].strip()
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")


@router.post("/write/expand-prompt")
async def admin_expand_prompt(secret: str = Query(...), request: Request = None):
    """Expand a simple idea into a detailed Maya image prompt for review/editing."""
    _check(secret)
    body = await request.json()
    idea = body.get("idea", "").strip()
    if not idea:
        raise HTTPException(status_code=400, detail="idea required.")

    import requests as req
    from app.config import MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL

    system = (
        "You are generating image prompts for an AI image model. "
        "The subject is Maya: beautiful young woman, long beachy wavy blonde hair with natural highlights, "
        "bright blue-green eyes, sun-kissed golden skin, hourglass figure, voluptuous curves. "
        "Maya's style is CASUAL, REAL, and EFFORTLESSLY SEXY — NOT high fashion, NOT editorial, NOT a photoshoot. "
        "Think: messy bun or air-dried wavy hair, crop tops, oversized tees knotted at the waist, low-rise jeans, "
        "string bikinis, athletic shorts, vintage band tees, bralettes, casual sundresses — everyday clothes that "
        "happen to look great on her body. NO satin gowns, NO ballgowns, NO couture, NO studio lighting setups. "
        "Settings should feel real: her bedroom (lived-in, unmade bed), a bar, a ski lodge, lake dock, "
        "friend's couch, car selfie, bathroom mirror, outdoor patio. "
        "Lighting should be natural — golden hour, morning light through blinds, neon bar light, phone flash. "
        "Pose is confident and natural — not posed like a model, more like she just looked up from her phone. "
        "Take the user's idea and write ONE detailed image generation prompt. "
        "Output ONLY the prompt text. No explanation, no quotes, no extra text."
    )
    payload = {
        "model":    MODELSLAB_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": idea},
        ],
    }
    headers = {"Authorization": f"Bearer {MODELSLAB_API_KEY}", "Content-Type": "application/json"}
    try:
        r = req.post(MODELSLAB_API_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        expanded = ""
        if "choices" in data:
            expanded = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        elif "output" in data:
            expanded = data["output"][0].strip().strip('"').strip("'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")
    if not expanded:
        raise HTTPException(status_code=500, detail="LLM returned empty prompt.")
    return {"expanded_prompt": expanded}


@router.post("/write/image")
async def admin_write_image(secret: str = Query(...), request: Request = None):
    """
    Take a simple idea, expand it into a full Maya image prompt via LLM,
    then generate the image. Returns the expanded prompt + image URL.
    """
    try:
        _check(secret)
        body = await request.json()
        idea = body.get("idea", "").strip()
        expanded = body.get("expanded_prompt", "").strip()

        from app.services.social_service import _generate_image

        if not expanded and not idea:
            raise HTTPException(status_code=400, detail="idea or expanded_prompt required.")
        if not expanded:
            raise HTTPException(status_code=400, detail="expanded_prompt required.")

        model_type      = body.get("model_type", "lora")
        character       = body.get("character", "mayaleja")
        negative_prompt = body.get("negative_prompt", "")

        image_url, img_error = _generate_image(expanded, model_type=model_type, character=character, negative_prompt=negative_prompt)

        if img_error and not image_url:
            raise HTTPException(status_code=500, detail=img_error)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e} | {traceback.format_exc()}")

    return {
        "expanded_prompt": expanded,
        "image_url": image_url,
    }


@router.post("/write/create")
async def admin_write_create(secret: str = Query(...), request: Request = None):
    """
    One-shot mobile create: generate image + caption in a single call.
    Body:
      scene_prompt   - what the image should look like
      model_type     - lora (default) | portrait | scene
      bg_image_url   - optional: background image for img2img
      blend          - 0.0–1.0 prompt_strength for img2img (default 0.8)
      caption_hint   - optional: if provided, optimize for platform instead of generating fresh
      platform       - threads | instagram | x (affects caption style)
    Returns: { image_url, caption }
    """
    _check(secret)
    body         = await request.json()
    scene_prompt = body.get("scene_prompt", "").strip()
    model_type   = body.get("model_type", "lora")
    character    = body.get("character", "mayaleja")
    bg_image_url = (body.get("bg_image_url") or "").strip() or None
    blend        = float(body.get("blend", 0.8))
    caption_hint = (body.get("caption_hint") or "").strip() or None
    platform     = body.get("platform", "instagram")

    if not scene_prompt:
        raise HTTPException(status_code=400, detail="scene_prompt required.")

    import requests as req
    from app.config import MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL
    from app.services.social_service import _generate_image, _generate_image_lora
    from app.ai.persona import load_persona

    # ── 1. Generate image ───────────────────────────────────────────────────
    if model_type == "lora" or bg_image_url:
        image_url, img_err = _generate_image_lora(
            scene_prompt,
            image_url=bg_image_url,
            prompt_strength=blend,
            character=character,
        )
    else:
        image_url, img_err = _generate_image(scene_prompt, model_type=model_type, character=character)

    if not image_url:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {img_err}")

    # ── 2. Generate or optimise caption ────────────────────────────────────
    platform_style = {
        "instagram": "Instagram — hook first line, warm and personal, ends with a soft CTA or question. 3–5 relevant hashtags on a new line.",
        "threads":   "Threads — 1–3 lines, dry wit or genuine moment, no hashtags, lowercase fine.",
        "x":         "X/Twitter — punchy, under 200 chars, optionally @mention a relevant account.",
    }.get(platform, "casual social media post")

    if caption_hint:
        user_msg = f"Optimise this caption for {platform_style}:\n\n{caption_hint}"
    else:
        user_msg = f"Write a caption for this image scene for {platform_style}:\n\nScene: {scene_prompt}"

    persona = load_persona()
    llm_payload = {
        "model": MODELSLAB_MODEL,
        "messages": [
            {"role": "system", "content": persona + "\n\nWrite only the caption text. No explanation."},
            {"role": "user",   "content": user_msg},
        ],
    }
    try:
        r = req.post(MODELSLAB_API_URL, json=llm_payload,
                     headers={"Authorization": f"Bearer {MODELSLAB_API_KEY}", "Content-Type": "application/json"},
                     timeout=30)
        r.raise_for_status()
        d = r.json()
        caption = (d.get("choices", [{}])[0].get("message", {}).get("content") or
                   (d.get("output") or [""])[0]).strip()
    except Exception as e:
        caption = caption_hint or scene_prompt  # fallback

    return {"image_url": image_url, "caption": caption}


PLATFORM_GUIDE = {
    "instagram": (
        "Instagram — strong hook on first line (no 'I' opener), warm and personal tone, "
        "2-3 sentences max, end with a question or soft CTA. Add 3-5 niche hashtags on a new line. "
        "Emojis OK but not excessive."
    ),
    "threads": (
        "Threads — 1-3 lines, conversational, dry wit or genuine moment works best. "
        "No hashtags. Lowercase is fine. No CTA. Should feel like a real thought, not a post."
    ),
    "x": (
        "X/Twitter — punchy, under 220 chars. Hook in the first 5 words. "
        "No hashtags unless very relevant. Can be provocative, funny, or insightful."
    ),
}


@router.post("/write/expand-activity")
async def admin_expand_activity(secret: str = Query(...), request: Request = None):
    """
    Turn a short activity word into a detailed Flux image prompt.
    Body: { activity, character ('mayaleja' or 'maya') }
    Returns: { prompt }
    """
    _check(secret)
    body      = await request.json()
    activity  = body.get("activity", "").strip()
    character = body.get("character", "mayaleja")
    if not activity:
        raise HTTPException(status_code=400, detail="activity required.")

    from app.config import MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL
    import requests as req

    trigger = "mayaleja" if character == "mayaleja" else "mayaselfie"
    user_msg = (
        f"Write a Flux image prompt for a photo of a woman associated with {activity}. "
        f"Focus on the SETTING and ENVIRONMENT — where she is, what's around her, lighting, mood, camera angle. "
        f"Avoid describing intense physical action or complex body poses — describe the scene she's in, not what her body is doing. "
        f"Do NOT describe her face or body appearance — the LoRA handles that. "
        f"Output only the prompt text, starting with '{trigger} solo', no explanation, no quotes."
    )

    try:
        r = req.post(
            MODELSLAB_API_URL,
            json={
                "model": MODELSLAB_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an expert Flux image prompt writer. Write concise, vivid, technically correct prompts."},
                    {"role": "user",   "content": user_msg},
                ],
            },
            headers={"Authorization": f"Bearer {MODELSLAB_API_KEY}", "Content-Type": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        d = r.json()
        prompt = (d.get("choices", [{}])[0].get("message", {}).get("content") or
                  (d.get("output") or [""])[0]).strip().strip('"')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    return {"prompt": prompt}


@router.post("/write/caption")
async def admin_write_caption(secret: str = Query(...), request: Request = None):
    """
    Generate or optimise a caption for a specific platform.
    Body: { platform, hint (optional), scene_prompt (optional), image_url (optional) }
    Returns: { caption }
    """
    _check(secret)
    body         = await request.json()
    platform     = body.get("platform", "instagram")
    hint         = (body.get("hint") or "").strip() or None
    scene_prompt = (body.get("scene_prompt") or "").strip() or None

    from app.config import MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL
    from app.ai.persona import load_persona
    import requests as req

    guide = PLATFORM_GUIDE.get(platform, PLATFORM_GUIDE["instagram"])

    if hint:
        user_msg = f"Rewrite this caption optimised for {guide}\n\nOriginal:\n{hint}"
    elif scene_prompt:
        user_msg = f"Write a caption for this image for {guide}\n\nImage scene: {scene_prompt}"
    else:
        user_msg = f"Write a short caption for {guide}"

    persona = load_persona()
    try:
        r = req.post(
            MODELSLAB_API_URL,
            json={
                "model": MODELSLAB_MODEL,
                "messages": [
                    {"role": "system", "content": persona + "\n\nWrite only the caption. No explanation, no quotes around it."},
                    {"role": "user",   "content": user_msg},
                ],
            },
            headers={"Authorization": f"Bearer {MODELSLAB_API_KEY}", "Content-Type": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        d = r.json()
        caption = (d.get("choices", [{}])[0].get("message", {}).get("content") or
                   (d.get("output") or [""])[0]).strip()
    except Exception:
        caption = hint or ""

    return {"caption": caption}


@router.post("/write/queue")
async def admin_write_queue(secret: str = Query(...), request: Request = None):
    """Queue a piece of text as a pending post."""
    _check(secret)
    body            = await request.json()
    caption         = body.get("caption", "").strip()
    image_url       = (body.get("image_url") or "").strip() or None
    target_platform = body.get("target_platform", "threads")
    if not caption:
        raise HTTPException(status_code=400, detail="caption required.")
    from app.db.crud import create_social_post
    post_id = create_social_post(caption=caption, image_url=image_url, target_platform=target_platform)
    return {"id": post_id, "caption": caption}


@router.post("/generate")
def generate_post_now(secret: str = Query(...), platform: str = Query("threads"), idea: str = Query(None)):
    _check(secret)
    if platform not in ("threads", "instagram", "x"):
        raise HTTPException(status_code=400, detail="platform must be threads, instagram, or x")
    from app.services.social_service import generate_post_for_queue
    from app.services.local_context_service import get_local_context
    context = get_local_context()
    result  = generate_post_for_queue(local_context=context, platform=platform, idea=idea)
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

@router.get("/ig-debug")
def ig_debug(secret: str = Query(...)):
    """Return raw Facebook API responses to diagnose Instagram account linking."""
    _check(secret)
    import requests as req
    from app.config import INSTAGRAM_ACCESS_TOKEN
    GRAPH = "https://graph.facebook.com/v19.0"

    if not INSTAGRAM_ACCESS_TOKEN:
        return {"error": "INSTAGRAM_ACCESS_TOKEN not set"}

    out = {}

    # 1. Who does this token belong to?
    r = req.get(f"{GRAPH}/me", params={"access_token": INSTAGRAM_ACCESS_TOKEN, "fields": "id,name"}, timeout=10)
    out["me"] = r.json()

    # 2. What pages does this token see?
    r2 = req.get(f"{GRAPH}/me/accounts",
                 params={"access_token": INSTAGRAM_ACCESS_TOKEN,
                         "fields": "id,name,instagram_business_account"},
                 timeout=10)
    out["pages"] = r2.json()

    # 3. Try fetching IG account directly on each page with page access token
    ig_details = []
    for page in r2.json().get("data", []):
        page_token_r = req.get(f"{GRAPH}/{page['id']}",
                               params={"access_token": INSTAGRAM_ACCESS_TOKEN,
                                       "fields": "access_token,instagram_business_account"},
                               timeout=10)
        ig_details.append({"page_id": page["id"], "page_name": page.get("name"), "detail": page_token_r.json()})
    out["page_details"] = ig_details

    # 4. Check token permissions
    r3 = req.get(f"{GRAPH}/me/permissions", params={"access_token": INSTAGRAM_ACCESS_TOKEN}, timeout=10)
    out["permissions"] = r3.json()

    return out


@router.get("/local-context")
def local_context_preview(secret: str = Query(...)):
    _check(secret)
    from app.services.local_context_service import get_local_context
    context = get_local_context()
    return {"context": context or "Nothing fetched — check RSS feeds or network."}


# ── Engagement API ────────────────────────────────────────────────────────────

@router.get("/engagement/comments")
def engagement_pending(secret: str = Query(...)):
    """List unanswered comments on Maya's recent Threads posts."""
    _check(secret)
    from app.services.social_engagement_service import fetch_pending_comments
    comments = fetch_pending_comments()
    return {"comments": comments}


@router.post("/engagement/run")
def engagement_run(secret: str = Query(...)):
    """Auto-reply to all unanswered comments."""
    _check(secret)
    from app.services.social_engagement_service import run_engagement_pass
    result = run_engagement_pass()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/engagement/preview-reply")
async def engagement_preview_reply(secret: str = Query(...), request: Request = None):
    """Generate a reply in Maya's voice without posting it."""
    _check(secret)
    body         = await request.json()
    comment_text = body.get("comment_text", "")
    post_caption = body.get("post_caption", "")
    if not comment_text:
        raise HTTPException(status_code=400, detail="comment_text required.")
    from app.services.social_engagement_service import _llm_reply
    reply = _llm_reply(comment_text, post_caption)
    if not reply:
        raise HTTPException(status_code=500, detail="LLM generation failed.")
    return {"reply": reply}


@router.post("/engagement/reply")
async def engagement_reply_one(secret: str = Query(...), request: Request = None):
    """Reply to a specific comment (optionally with custom text)."""
    _check(secret)
    body        = await request.json()
    comment_id  = body.get("comment_id", "")
    post_id     = body.get("post_id", "")
    post_caption = body.get("post_caption", "")
    comment_text = body.get("comment_text", "")
    reply_text  = body.get("reply_text")  # optional — generate if not provided

    if not comment_id or not comment_text:
        raise HTTPException(status_code=400, detail="comment_id and comment_text required.")

    from app.services.social_engagement_service import reply_to_comment
    result = reply_to_comment(
        comment_id=comment_id,
        post_id=post_id,
        post_caption=post_caption,
        comment_text=comment_text,
        reply_text=reply_text,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "Reply failed."))
    return result


@router.post("/engagement/comment-on")
async def engagement_comment_on(secret: str = Query(...), request: Request = None):
    """Post an outbound comment on any Threads post by ID."""
    _check(secret)
    body       = await request.json()
    thread_id  = body.get("thread_id", "")
    topic      = body.get("topic", "")
    custom_text = body.get("custom_text", "")

    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id required.")

    from app.services.social_engagement_service import post_outbound_comment
    result = post_outbound_comment(thread_id=thread_id, topic=topic, custom_text=custom_text)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed."))
    return result


@router.get("/engagement/history")
def engagement_history(secret: str = Query(...)):
    """Recent comment replies Maya has sent."""
    _check(secret)
    from app.db.crud import get_recent_comment_replies
    return {"replies": get_recent_comment_replies(limit=50)}


@router.get("/engagement/x-mentions")
def engagement_x_mentions(secret: str = Query(...)):
    """Fetch recent @mentions on X that haven't been replied to."""
    _check(secret)
    try:
        from app.services.x_service import get_mentions
        mentions = get_mentions()
        return {"mentions": mentions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engagement/x-reply")
async def engagement_x_reply(secret: str = Query(...), request: Request = None):
    """Reply to a specific tweet as Maya."""
    _check(secret)
    body       = await request.json()
    tweet_id   = body.get("tweet_id", "")
    reply_text = body.get("reply_text", "")
    if not tweet_id or not reply_text:
        raise HTTPException(status_code=400, detail="tweet_id and reply_text required.")
    try:
        from app.services.x_service import post_reply
        result = post_reply(reply_text, reply_to_id=tweet_id)
        from app.db.crud import log_comment_reply
        log_comment_reply(platform="x", comment_id=tweet_id, post_id=tweet_id, reply_text=reply_text, platform_reply_id=str(result["id"]))
        return {"ok": True, "reply": reply_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engagement/find-posts")
def engagement_find_posts(secret: str = Query(...)):
    """Search Threads for posts Maya can comment on, with draft comments."""
    _check(secret)
    from app.services.social_engagement_service import preview_outbound_comments
    previews = preview_outbound_comments(max_results=6)
    return {"posts": previews}


# ── Video (Kling) ─────────────────────────────────────────────────────────────

@router.post("/video/image-to-video")
async def video_image_to_video(secret: str = Query(...), request: Request = None):
    """Animate an image URL into a video using Kling."""
    _check(secret)
    body      = await request.json()
    image_url = body.get("image_url", "")
    prompt    = body.get("prompt", "")
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url required.")
    from app.services.kling_service import image_to_video
    url, err = image_to_video(image_url, prompt=prompt)
    if err:
        raise HTTPException(status_code=500, detail=err)
    return {"video_url": url}


@router.post("/video/text-to-video")
async def video_text_to_video(secret: str = Query(...), request: Request = None):
    """Generate a video from a text prompt using Kling."""
    _check(secret)
    body   = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required.")
    from app.services.kling_service import text_to_video
    url, err = text_to_video(prompt)
    if err:
        raise HTTPException(status_code=500, detail=err)
    return {"video_url": url}


@router.post("/posts/carousel")
async def post_carousel(secret: str = Query(...), request: Request = None):
    """Post a carousel of images to Instagram."""
    _check(secret)
    body       = await request.json()
    caption    = body.get("caption", "").strip()
    image_urls = body.get("image_urls", [])
    hashtags   = body.get("hashtags")
    if not caption or len(image_urls) < 2:
        raise HTTPException(status_code=400, detail="caption and at least 2 image_urls required.")
    from app.db.crud import create_social_post
    from app.services.instagram_service import post_carousel_to_instagram
    post_id = create_social_post(caption=caption, target_platform="instagram")
    ok = post_carousel_to_instagram(post_id, caption, image_urls, hashtags=hashtags)
    if not ok:
        raise HTTPException(status_code=500, detail="Carousel post failed — check logs.")
    return {"ok": True, "post_id": post_id}


@router.post("/posts/reel")
async def post_reel(secret: str = Query(...), request: Request = None):
    """Post a Reel to Instagram from a video URL."""
    _check(secret)
    body      = await request.json()
    caption   = body.get("caption", "").strip()
    video_url = body.get("video_url", "").strip()
    hashtags  = body.get("hashtags")
    if not caption or not video_url:
        raise HTTPException(status_code=400, detail="caption and video_url required.")
    from app.db.crud import create_social_post
    from app.services.instagram_service import post_reel_to_instagram
    post_id = create_social_post(caption=caption, target_platform="instagram")
    ok = post_reel_to_instagram(post_id, caption, video_url, hashtags=hashtags)
    if not ok:
        raise HTTPException(status_code=500, detail="Reel post failed — check logs.")
    return {"ok": True, "post_id": post_id}


@router.post("/instagram/token")
async def set_instagram_token(secret: str = Query(...), request: Request = None):
    """Seed or replace the stored Instagram long-lived token."""
    _check(secret)
    body  = await request.json()
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="token required.")
    from app.db.crud import set_app_token
    set_app_token("instagram_access_token", token)
    return {"ok": True, "message": "Token saved. It will auto-refresh every 50 days."}


@router.post("/instagram/refresh-token")
async def refresh_instagram_token_endpoint(secret: str = Query(...)):
    """Manually trigger an Instagram token refresh."""
    _check(secret)
    from app.services.instagram_service import refresh_instagram_token
    new_token = refresh_instagram_token()
    if not new_token:
        raise HTTPException(status_code=500, detail="Token refresh failed — check logs.")
    return {"ok": True, "message": "Token refreshed and stored."}
