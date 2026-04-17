"""
Social media service for Maya.
Generates posts in Maya's voice and publishes to X (Twitter).
Instagram slot is stubbed — wire in when Meta API access is ready.

tweepy is imported lazily so the app doesn't crash if X keys aren't set yet.
"""
import random
import requests

# Consistent character description prepended to every image prompt
MAYA_CHARACTER = (
    "young woman, long beachy wavy blonde hair, thin waist, fit toned body, "
    "subtle curves, naturally pretty face, sun-kissed skin, subtly sexy, "
    "candid lifestyle photo, "
)
from app.config import (
    MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL,
    MODELSLAB_IMAGE_URL,
    MODELSLAB_PORTRAIT_MODEL, MODELSLAB_SCENE_MODEL,
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
)
from app.ai.persona import load_persona
from app.db.crud import (
    create_social_post, approve_post,
    mark_post_posted, mark_post_failed
)


POST_TYPES = [
    {
        "type":       "day_to_day",
        "weight":     12,
        "prompt":     "Write a single post as Maya — something random from her day. Could be anything: a weird interaction, something she noticed, a small win or frustration, a thought she had driving around Tahoe. Real and unfiltered. Lowercase sometimes. Under 220 characters. No hashtags. Just the text.",
        "with_image": False,
    },
    {
        "type":       "coffee_barista",
        "weight":     10,
        "prompt":     "Write a post as Maya about coffee. She takes coffee seriously — pour-overs, dialing in espresso, the difference a good grind makes, a customer who ordered something wrong, a perfect shot she pulled. Specific and real. Under 200 characters. No hashtags.",
        "with_image": False,
    },
    {
        "type":         "selfie_vibe",
        "weight":       10,
        "prompt":       "Write a short caption Maya would post with a selfie or candid photo. One line, a mood, or just a feeling. Lowercase, no hashtags. Under 90 characters. Just the caption.",
        "with_image":   True,
        "image_model":  "portrait",
        "image_prompt": "selfie, south lake tahoe, golden hour sunlight, natural lighting, warm tones, hyperrealistic",
    },
    {
        "type":       "bar_shift",
        "weight":     8,
        "prompt":     "Write a post as Maya about a bar shift. Something she observed, a drink she made, a customer who tested her patience, a slow Tuesday, a chaotic Saturday. Dry and real. Under 200 characters. No hashtags.",
        "with_image": False,
    },
    {
        "type":         "snowboarding",
        "weight":       8,
        "prompt":       "Write a post as Maya about snowboarding at Squaw Valley (she calls it Squaw, never Palisades). Something real — conditions, a specific run, who she went with, what the day felt like. Under 200 characters. Lowercase fine. No hashtags.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "snowboarding squaw valley tahoe, deep powder, alpine peaks, action shot, ski jacket, snow pants, hyperrealistic",
    },
    {
        "type":       "house_music",
        "weight":     8,
        "prompt":     "Write a post as Maya about house music. She loves it — classic tracks, new releases, a DJ set she heard, a song that hits different at 2am, the feeling of a good bassline. Could reference real artists or tracks. Under 200 characters. No hashtags.",
        "with_image": False,
    },
    {
        "type":       "craft_beer",
        "weight":     8,
        "prompt":     "Write a post as Maya about craft beer. She's into microbrews, especially citrus IPAs. Could be about a specific brew she's trying, a new tap at the bar, what pairs well, or just appreciating a cold one after a long shift. Under 200 characters. No hashtags.",
        "with_image": False,
    },
    {
        "type":       "travel",
        "weight":     8,
        "prompt":     "Write a post as Maya about travel or wanting to travel. Could be a trip she took, a place on her list, somewhere she's been that surprised her, or just wanderlust hitting on a slow day. Real and specific, not generic. Under 220 characters. No hashtags.",
        "with_image": False,
    },
    {
        "type":         "lake_day",
        "weight":       8,
        "prompt":       "Write a post as Maya about a day at Lake Tahoe — on the water, at the beach, paddleboarding, watching the sunset, just floating around. Short and feels like summer. Under 180 characters. No hashtags.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "lake tahoe summer, crystal blue water, dock, bikini, golden hour, hyperrealistic",
    },
    {
        "type":       "festival",
        "weight":     7,
        "prompt":     "Write a post as Maya about a music festival or big event — could be Coachella, Outside Lands, a local fest, or just the idea of festival season. Something real about the experience: the crowd, the lineup, the chaos, the good parts. Under 200 characters. No hashtags.",
        "with_image": False,
    },
    {
        "type":       "dog_content",
        "weight":     7,
        "prompt":     "Write a post as Maya about wanting a dog, or about a dog she saw, or thinking about what kind of dog she'd get. She really wants one but her life is too chaotic right now. Genuine and a little wistful. Under 200 characters. No hashtags.",
        "with_image": False,
    },
    {
        "type":       "music_show",
        "weight":     6,
        "prompt":     "Write a post as Maya about going to a show or wishing she was at one. Could be a club night, a small venue, a DJ set, or a festival stage. What she heard, how it felt, who she went with. Under 200 characters. No hashtags.",
        "with_image": False,
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


def _generate_image(prompt: str, model_type: str = "scene") -> str | None:
    model = MODELSLAB_PORTRAIT_MODEL if model_type == "portrait" else MODELSLAB_SCENE_MODEL
    payload = {
        "key":                 MODELSLAB_API_KEY,
        "model_id":            model,
        "prompt":              MAYA_CHARACTER + prompt,
        "negative_prompt":     "bad quality, blurry, distorted, watermark, text, deformed hands, extra limbs, plastic skin, overexposed, ugly, lowres, amateur, man, male, old, wrinkles",
        "width":               "768",
        "height":              "768",
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
        model_type   = post_cfg.get("image_model", "scene")
        image_url    = _generate_image(image_prompt, model_type=model_type)

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
