"""
Social media service for Maya.
Generates posts in Maya's voice and publishes to X (Twitter).
Instagram slot is stubbed — wire in when Meta API access is ready.

tweepy is imported lazily so the app doesn't crash if X keys aren't set yet.
"""
import random
import requests
from app.config import (
    MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL,
    MODELSLAB_IMAGE_URL, MODELSLAB_IMAGE_MODEL,
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
)
from app.ai.persona import load_persona
from app.db.crud import (
    create_social_post, approve_post,
    mark_post_posted, mark_post_failed
)


POST_TYPES = [
    {
        "type":       "text_only",
        "weight":     40,
        "prompt":     "Write a single tweet as Maya. Raw, lowercase sometimes, no hashtags, no emojis unless it genuinely fits. Could be about the mountain, bar shift, something she noticed, something on her mind. Under 240 characters. Just the tweet text, nothing else.",
        "with_image": False,
    },
    {
        "type":         "mountain",
        "weight":       25,
        "prompt":       "Write a tweet as Maya about snowboarding at Squaw Valley (she calls it Squaw, never Palisades). Something real — conditions, a run, who she saw, what the day felt like. Under 200 characters. Lowercase fine. No hashtags. Just the tweet.",
        "with_image":   True,
        "image_prompt": "woman snowboarding squaw valley tahoe mountains powder day action shot photorealistic",
    },
    {
        "type":       "bar_shift",
        "weight":     20,
        "prompt":     "Write a tweet as Maya about a bar shift. Something she saw, someone who annoyed her, a drink she made, an observation. Real and dry. Under 200 characters. Just the tweet.",
        "with_image": False,
    },
    {
        "type":         "selfie_vibe",
        "weight":       15,
        "prompt":       "Write a very short caption Maya would post with a photo. Under 100 characters. Could be one line or a mood. Lowercase, no hashtags. Just the caption.",
        "with_image":   True,
        "image_prompt": "beautiful woman south lake tahoe california natural lighting candid photorealistic warm tones",
    },
]


def _generate_caption(post_prompt: str, context: str = "") -> str | None:
    """Call the LLM to write a post in Maya's voice."""
    persona = load_persona()
    system  = persona
    if context:
        system += f"\n\n---\nCurrent local context (use naturally if relevant):\n{context}"
    system += "\n\nYou are generating social media content as Maya. Stay completely in character."

    payload = {
        "model":    MODELSLAB_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": post_prompt},
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
        print(f"SOCIAL LLM ERROR: {e}")

    return None


def _generate_image(prompt: str) -> str | None:
    payload = {
        "key":                 MODELSLAB_API_KEY,
        "model_id":            MODELSLAB_IMAGE_MODEL,
        "prompt":              prompt,
        "negative_prompt":     "bad quality, blurry, distorted, watermark, text",
        "width":               "1024",
        "height":              "1024",
        "samples":             "1",
        "num_inference_steps": "30",
        "guidance_scale":      7.5,
        "safety_checker":      "no",
    }
    try:
        r = requests.post(MODELSLAB_IMAGE_URL, json=payload,
                          headers={"Content-Type": "application/json"}, timeout=60)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            return data["output"][0]
        if data.get("status") == "processing":
            return data.get("future_links", [None])[0]
    except Exception as e:
        print(f"SOCIAL IMAGE ERROR: {e}")
    return None


def generate_post_for_queue(local_context: str = "") -> dict | None:
    """
    Generate a post and add to the approval queue.
    Pass local_context (current Tahoe news/weather) to make posts topical.
    """
    weights  = [p["weight"] for p in POST_TYPES]
    post_cfg = random.choices(POST_TYPES, weights=weights, k=1)[0]

    caption = _generate_caption(post_cfg["prompt"], context=local_context)
    if not caption:
        return None

    image_url    = None
    image_prompt = None

    if post_cfg.get("with_image"):
        image_prompt = post_cfg.get("image_prompt", "")
        image_url    = _generate_image(image_prompt)

    # Always generate a branded text card if no image was produced
    # so every post has a visual for Instagram
    if not image_url:
        from app.services.image_service import upload_text_card
        image_url = upload_text_card(caption)
        if image_url:
            print(f"SOCIAL: generated text card — {image_url}")

    post_id = create_social_post(
        caption=caption,
        image_url=image_url,
        image_prompt=image_prompt,
    )

    print(f"SOCIAL: queued post #{post_id} — {caption[:60]}...")
    return {"id": post_id, "caption": caption, "image_url": image_url}


def post_to_x(post_id: int, caption: str, image_url: str = None) -> bool:
    """Publish an approved post to X. Imports tweepy lazily."""
    try:
        import tweepy
        import tempfile, os

        client   = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
        )
        media_id = None

        if image_url:
            img_resp = requests.get(image_url, timeout=30)
            img_resp.raise_for_status()

            auth   = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET,
                                              X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
            api_v1 = tweepy.API(auth)

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(img_resp.content)
                tmp_path = tmp.name

            try:
                media    = api_v1.media_upload(tmp_path)
                media_id = str(media.media_id)
            finally:
                os.unlink(tmp_path)

        tweet_kwargs = {"text": caption}
        if media_id:
            tweet_kwargs["media_ids"] = [media_id]

        response         = client.create_tweet(**tweet_kwargs)
        platform_post_id = str(response.data["id"])
        mark_post_posted(post_id, platform_post_id)
        print(f"SOCIAL: posted to X — tweet id {platform_post_id}")
        return True

    except Exception as e:
        print(f"SOCIAL X ERROR: {e}")
        mark_post_failed(post_id)
        return False


def post_to_instagram(post_id: int, caption: str, image_url: str = None) -> bool:
    raise NotImplementedError("Instagram integration pending Meta API approval.")
