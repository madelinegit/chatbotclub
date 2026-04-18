"""
Social media service for Maya.
Generates posts in Maya's voice and publishes to X (Twitter) and Instagram.
"""
import random
import datetime
import requests

# Consistent character description prepended to every image prompt
MAYA_CHARACTER = (
    "beautiful young woman, long beachy wavy blonde hair with natural highlights, "
    "bright blue-green eyes, sun-kissed golden skin, defined cheekbones, full lips, "
    "thin waist, toned fit body, voluptuous figure, large round butt, ample cleavage, "
    "hourglass curves, subtly sexy confident pose, "
    "High Detail, Perfect Composition, cinematic lighting, photorealistic, 8k, "
)
from app.config import (
    MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL,
    MODELSLAB_IMAGE_URL,
    MODELSLAB_PORTRAIT_MODEL, MODELSLAB_SCENE_MODEL, MODELSLAB_EXPLICIT_MODEL,
    MODELSLAB_LORA_MODEL, MODELSLAB_FLUX_BASE,
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
)
from app.ai.persona import load_persona
from app.db.crud import (
    create_social_post, approve_post,
    mark_post_posted, mark_post_failed
)


# Weekday personality modes — injected into every post prompt
WEEKDAY_MODES = {
    0: ("dry",       "Today Maya is at her most deadpan. Flat delivery, dry observations, zero explanation. The joke is the understatement."),
    1: ("flirty",    "Today Maya is confident and casually flirty. Aware of herself. Says something and knows exactly how it lands."),
    2: ("existential","Today Maya is questioning things. Not depressed — just staring at the ceiling kind of mood. Unfiltered."),
    3: ("basic",     "Today Maya is unironically into normal things. PSLs, good playlists, small victories. No irony. She means it."),
    4: ("sincere",   "Today Maya drops the armor. One genuine moment — warm, real, no performance. Still her, just soft."),
    5: ("chaotic",   "Weekend energy. Maya is unpredictable — could be anything. Don't explain it."),
    6: ("chaotic",   "Weekend energy. Maya is unpredictable — could be anything. Don't explain it."),
}

# Instagram hashtag sets per post type — rotated, 3-5 tags, appended only on IG
HASHTAG_SETS = {
    "selfie_vibe":   ["#TahoeLife #GoldenHour #LakeTahoe", "#TahoeGirl #LifeInTahoe #Vibes", "#CandidShot #TahoeVibes #SunsetGirl"],
    "snowboarding":  ["#SquawValley #PowderDay #Snowboarding", "#TahoeWinter #RideOrDie #SnowLife", "#FreerideLife #MountainGirl #Shred"],
    "lake_day":      ["#LakeTahoe #TahoeBlue #LakeLife", "#SummerVibes #PaddleBoard #TahoeSummer", "#LakeDays #ClearWater #TahoeNation"],
    "coffee_barista":["#CoffeeLover #BaristaLife #PourOver", "#EspressoShots #CoffeeTime #BrewedPerfectly", "#CaffeineAndVibes #CoffeeFirst #BaristaDiaries"],
    "bar_shift":     ["#BehindTheBar #BarLife #NightShift", "#Bartender #LateNightVibes #BarCulture", "#OnTap #ShiftDrink #BarNotes"],
    "day_to_day":    ["#TahoeLife #RealLife #JustLiving", "#TahoeLocal #EverydayMoments #Unfiltered", "#SliceOfLife #TahoeMoments #Authentic"],
    "travel":        ["#WanderlustLife #TravelGirl #ExploreMore", "#AlwaysMoving #TravelVibes #NextDestination", "#PassportReady #TravelDiaries #Roaming"],
    "house_music":   ["#HouseMusic #DanceFloor #NightLife", "#DeepHouse #TechHouse #MusicIsLife", "#EcstaticDance #SoundSystem #DJSet"],
    "festival":      ["#FestivalSeason #FestivalLife #GoodVibes", "#MusicFestival #OutsideLands #LiveMusic", "#FestivalStyle #Coachella #CrowdEnergy"],
    "dog_content":   ["#DogMom #PuppyLove #NeedADog", "#DogLife #IWantADog #Someday", "#FutureDogMom #DogObsessed #PleaseAdoptMe"],
    "craft_beer":    ["#CraftBeer #IPA #BrewLife", "#LocalBrew #TapRoom #BeerOClock", "#CraftBeerLover #HopHead #MicroBrew"],
    "music_show":    ["#LiveMusic #ConcertLife #NightOut", "#MusicScene #ShowNight #GoodSounds", "#LocalScene #DJNight #MusicVibes"],
}

POST_TYPES = [
    {
        "type":       "day_to_day",
        "weight":     12,
        "prompt":     "Write 1–3 lines as Maya — something from her day. A weird interaction, something she noticed, a small frustration, a random thought. Real and unfiltered. No explanation. No hashtags. Lowercase fine. Output only the post text.",
        "with_image": False,
    },
    {
        "type":       "coffee_barista",
        "weight":     10,
        "prompt":     "Write 1–3 lines as Maya about coffee. She's a barista who takes it seriously — a shot she pulled, a customer, a grind setting, something that annoyed her or didn't. Specific. Dry. No hashtags. No explanation. Just the post.",
        "with_image": False,
    },
    {
        "type":         "selfie_vibe",
        "weight":       10,
        "prompt":       "Write 1 line — a caption Maya posts with a photo of herself. A mood, a feeling, or nothing at all. Lowercase. No hashtags. Don't explain it. Just the line.",
        "with_image":   True,
        "image_model":  "portrait",
        "image_prompt": "mirror selfie or front camera selfie, wearing a low-cut fitted crop top showing subtle cleavage, hip tilted to the side showing off curves and butt, gold hoop earrings, subtle smoky eye makeup, glossy lips, South Lake Tahoe mountains in background, golden hour sunlight, warm amber tones, confident sultry expression, candid, High Detail, Perfect Composition, vibrant",
    },
    {
        "type":       "bar_shift",
        "weight":     8,
        "prompt":     "Write 1–3 lines as Maya about a bar shift. A customer, a drink, an observation, a moment. Dry. Real. No hashtags. No setup-punchline format. Just what she'd actually post.",
        "with_image": False,
    },
    {
        "type":         "snowboarding",
        "weight":       8,
        "prompt":       "Write 1–3 lines as Maya about snowboarding at Squaw (she calls it Squaw, never Palisades). Conditions, a run, a feeling. Real. Lowercase fine. No hashtags. Output only the post.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "snowboarding down steep powder run, fitted colorful ski jacket unzipped slightly, form-fitting snow pants, goggles pushed up on forehead, hair blowing in wind, Squaw Valley alpine peaks and blue sky behind her, action shot mid-turn, snow spray, dynamic pose, High Detail, Perfect Composition, vibrant colors, cinematic",
    },
    {
        "type":       "house_music",
        "weight":     8,
        "prompt":     "Write 1–3 lines as Maya about house music. A track, a set, a feeling at 2am, a bassline. Could name a real artist. No hashtags. Don't explain what house music is. Just the post.",
        "with_image": False,
    },
    {
        "type":       "craft_beer",
        "weight":     8,
        "prompt":     "Write 1–3 lines as Maya about craft beer. Specific — a brew she's trying, something on tap, what it pairs with, how it tastes. No hashtags. No fluff. Just the post.",
        "with_image": False,
    },
    {
        "type":       "travel",
        "weight":     8,
        "prompt":     "Write 1–3 lines as Maya about travel — a trip she took, a place she wants to go, a memory. Specific, not generic. No hashtags. No 'wanderlust' language. Just the post.",
        "with_image": False,
    },
    {
        "type":         "lake_day",
        "weight":       8,
        "prompt":       "Write 1–2 lines as Maya about Lake Tahoe — on the water, at the beach, paddleboarding, watching the sunset. Short. Feels like summer. No hashtags. Output only the caption.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "standing on wooden dock at Lake Tahoe, wearing a small string bikini, hip tilted showing off curves and round butt, facing slightly away then glancing back over shoulder, crystal blue water and Sierra Nevada mountains behind her, golden hour warm light on skin, hair tousled by breeze, High Detail, Perfect Composition, vibrant, cinematic lighting",
    },
    {
        "type":       "festival",
        "weight":     7,
        "prompt":     "Write 1–3 lines as Maya about a music festival — Coachella, Outside Lands, something local. The crowd, the set, the chaos, the good part. Real. No hashtags. No hype language. Just the post.",
        "with_image": False,
    },
    {
        "type":       "dog_content",
        "weight":     7,
        "prompt":     "Write 1–2 lines as Maya about wanting a dog, or a dog she saw, or what kind she'd get someday. Her life is too chaotic right now but she still wants one. Genuine. No hashtags.",
        "with_image": False,
    },
    {
        "type":       "music_show",
        "weight":     6,
        "prompt":     "Write 1–3 lines as Maya about going to a show — a club night, small venue, DJ set. What she heard, how it felt. No hashtags. No recap format. Just the post.",
        "with_image": False,
    },
]


def _generate_caption(post_prompt: str, context: str = "", weekday_note: str = "") -> str | None:
    """Call the LLM to write a post in Maya's voice."""
    persona = load_persona()
    system  = persona
    if context:
        system += f"\n\n---\nCurrent local context (use naturally if relevant):\n{context}"
    system += (
        "\n\nYou are generating social media content as Maya. Stay completely in character."
        "\nRules: 1–3 lines maximum. Never explain the joke. Never add hashtags. Never use calls to action."
        "\nOutput only the post text — no quotes, no labels, no commentary."
    )
    if weekday_note:
        system += f"\n\nToday's voice note: {weekday_note}"

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


def _generate_image(prompt: str, model_type: str = "scene") -> tuple[str | None, str | None]:
    """Returns (image_url, error_message). One of them will be None."""
    lora_weights = []
    if model_type == "portrait":
        model = MODELSLAB_PORTRAIT_MODEL
    elif model_type == "explicit":
        model = MODELSLAB_EXPLICIT_MODEL
    elif model_type == "lora":
        model = MODELSLAB_FLUX_BASE
        if not MODELSLAB_LORA_MODEL:
            return None, "MODELSLAB_LORA_MODEL not set in Railway env vars"
        # ModelsLab expects HuggingFace repo ID (user/repo), not full URL
        lora_id = MODELSLAB_LORA_MODEL
        if lora_id.startswith("https://huggingface.co/"):
            lora_id = lora_id.replace("https://huggingface.co/", "").split("/resolve/")[0]
        lora_weights = lora_id
    else:
        model = MODELSLAB_SCENE_MODEL
    if not MODELSLAB_API_KEY:
        return None, "MODELSLAB_API_KEY not set in Railway env vars"
    if not model:
        return None, f"MODELSLAB_{model_type.upper()}_MODEL not set in Railway env vars"
    if not MODELSLAB_IMAGE_URL:
        return None, "MODELSLAB_IMAGE_URL not set in Railway env vars"

    # LoRA uses Flux — different scheduler and steps
    is_flux = model_type == "lora"
    full_prompt = ("mayavip " if is_flux else "") + MAYA_CHARACTER + prompt

    payload = {
        "key":                 MODELSLAB_API_KEY,
        "model_id":            model,
        "prompt":              full_prompt,
        "negative_prompt":     "(worst quality:2), (low quality:2), (normal quality:2), (jpeg artifacts), (blurry), (duplicate), (morbid), (mutilated), (out of frame), (extra limbs), (bad anatomy), (disfigured), (deformed), (cross-eye), (glitch), (oversaturated), (overexposed), (underexposed), (bad proportions), (bad hands), (bad feet), (cloned face), (long neck), (missing arms), (missing legs), (extra fingers), (fused fingers), (poorly drawn hands), (poorly drawn face), (mutation), (deformed eyes), watermark, text, logo, signature, grainy, censored, ugly, noisy image, bad lighting, unnatural skin, asymmetry, man, male, old, wrinkles",
        "width":               "768",
        "height":              "768",
        "samples":             "1",
        "num_inference_steps": "30" if is_flux else "31",
        "scheduler":           "EulerDiscreteScheduler" if is_flux else "DPMSolverMultistepScheduler",
        "guidance_scale":      3.5 if is_flux else 7.5,
        "enhance_prompt":      False,
        "safety_checker":      "no",
        "lora_model":          lora_weights if lora_weights else None,
        "lora_strength":       "0.9" if lora_weights else None,
    }
    if not lora_weights:
        del payload["lora_model"]
        del payload["lora_strength"]

    try:
        print(f"IMAGE GEN: posting to {MODELSLAB_IMAGE_URL} model={model} lora={lora_weights}")
        r = requests.post(MODELSLAB_IMAGE_URL, json=payload,
                          headers={"Content-Type": "application/json"}, timeout=90)
        print(f"IMAGE GEN: status={r.status_code} response={r.text[:300]}")
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            return data["output"][0], None
        if data.get("status") == "processing":
            return data.get("future_links", [None])[0], None
        return None, f"Unexpected ModelsLab response: {data}"
    except requests.exceptions.Timeout:
        return None, "ModelsLab request timed out after 75s — server may be overloaded"
    except requests.exceptions.HTTPError as e:
        return None, f"ModelsLab HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def generate_post_for_queue(local_context: str = "") -> dict | None:
    """
    Generate a post and add to the approval queue.
    Pass local_context (current Tahoe news/weather) to make posts topical.
    """
    weekday     = datetime.datetime.now().weekday()
    _, weekday_note = WEEKDAY_MODES.get(weekday, (None, ""))

    weights  = [p["weight"] for p in POST_TYPES]
    post_cfg = random.choices(POST_TYPES, weights=weights, k=1)[0]

    caption = _generate_caption(post_cfg["prompt"], context=local_context, weekday_note=weekday_note)
    if not caption:
        return None

    image_url    = None
    image_prompt = None

    if post_cfg.get("with_image"):
        image_prompt = post_cfg.get("image_prompt", "")
        model_type   = post_cfg.get("image_model", "scene")
        image_url, _ = _generate_image(image_prompt, model_type=model_type)

    # Pick a hashtag set for Instagram (rotated randomly)
    hashtag_options = HASHTAG_SETS.get(post_cfg["type"], [])
    hashtags = random.choice(hashtag_options) if hashtag_options else None

    post_id = create_social_post(
        caption=caption,
        image_url=image_url,
        image_prompt=image_prompt,
        hashtags=hashtags,
    )

    print(f"SOCIAL: queued post #{post_id} [{WEEKDAY_MODES[weekday][0]}] — {caption[:60]}...")
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
