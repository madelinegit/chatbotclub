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
    "toned athletic fit body, confident natural pose, "
    "High Detail, Perfect Composition, cinematic lighting, photorealistic, 8k, "
)
from app.config import (
    MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL,
    MODELSLAB_IMAGE_URL,
    MODELSLAB_PORTRAIT_MODEL, MODELSLAB_SCENE_MODEL, MODELSLAB_EXPLICIT_MODEL,
    REPLICATE_API_TOKEN, REPLICATE_LORA_VERSION,
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
)
from app.ai.persona import load_persona
from app.db.crud import (
    create_social_post,
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
    "selfie_vibe":    ["#TahoeLife #GoldenHour #LakeTahoe", "#TahoeGirl #MountainLife #SierraNevada", "#TahoeVibes #SunsetGirl #LifeInTahoe"],
    "snowboarding":   ["#SquawValley #PowderDay #Snowboarding", "#TahoeWinter #MountainGirl #Shred", "#FreerideLife #SierraNevada #PowderHound"],
    "lake_day":       ["#LakeTahoe #TahoeBlue #LakeLife", "#SummerInTahoe #PaddleBoard #ClearWater", "#TahoeSummer #AlpineLake #TahoeNation"],
    "coffee":         ["#CoffeeLover #PourOver #EspressoShots", "#CoffeeTime #SpecialtyCoffee #MorningRitual", "#CaffeineAndVibes #CoffeeFirst #BrewedPerfectly"],
    "day_to_day":     ["#TahoeLife #RealLife #TahoeLocal", "#EverydayMoments #Unfiltered #SliceOfLife", "#TahoeMoments #Authentic #MountainLiving"],
    "travel":         ["#TravelGirl #ExploreMore #AlwaysMoving", "#PassportReady #TravelDiaries #SoloTravel", "#WorldTraveler #TravelLife #Roaming"],
    "yoga_wellness":  ["#YogaLife #MorningPractice #MindfulMovement", "#YogaGirl #BodyAndMind #MoveYourBody", "#YogaEveryday #Breathe #YogaCommunity"],
    "outdoors_hiking":["#TahoeHikes #TrailLife #OutdoorLife", "#HikingGirl #SierraNevada #NatureTherapy", "#TrailRunning #GetOutside #MountainLife"],
    "dog_content":    ["#DogMom #PuppyLove #NeedADog", "#DogLife #FutureDogMom #Someday", "#DogObsessed #IWantADog #PleaseAdoptMe"],
    "food_cooking":   ["#FoodLover #CookingLife #HomeCook", "#EatWell #FoodPhotography #TasteEverything", "#FoodCulture #CookingFromScratch #FoodFirst"],
    "music_taste":    ["#LiveMusic #MusicLover #GoodSounds", "#MusicScene #ConcertLife #SoundSystem", "#MusicIsLife #LocalScene #ShowNight"],
    "bar_observation": [],
    "desert_art":     [],
}

POST_TYPES = [
    # ── High frequency: wholesome, aspirational, sharp ──────────────────────────
    {
        "type":       "day_to_day",
        "weight":     15,
        "prompt":     "Write 1–3 lines as Maya — a dry observation, a weird interaction, a small frustration, a random thought. Snarky but not bitter. Smart but not try-hard. No alcohol. No bar. No hashtags. Lowercase fine. Output only the post.",
        "with_image": False,
    },
    {
        "type":         "snowboarding",
        "weight":       13,
        "prompt":       "Write 1–3 lines as Maya about snowboarding at Squaw (she calls it Squaw, never Palisades). Conditions, a run, a feeling, gear, mountain culture. Real and specific. No hashtags. Output only the post.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "snowboarding down steep powder run, fitted colorful ski jacket unzipped slightly, form-fitting snow pants, goggles pushed up on forehead, hair blowing in wind, Squaw Valley alpine peaks and blue sky behind her, action shot mid-turn, snow spray, dynamic pose, High Detail, Perfect Composition, vibrant colors, cinematic",
    },
    {
        "type":         "selfie_vibe",
        "weight":       12,
        "prompt":       "Write 1 line — a caption Maya posts with a photo of herself. A mood, a feeling, or nothing at all. Confident not thirsty. Lowercase. No hashtags. Don't explain it. Just the line.",
        "with_image":   True,
        "image_model":  "portrait",
        "image_prompt": "mirror selfie or front camera selfie, wearing a low-cut fitted crop top showing subtle cleavage, hip tilted to the side showing off curves and butt, gold hoop earrings, subtle smoky eye makeup, glossy lips, South Lake Tahoe mountains in background, golden hour sunlight, warm amber tones, confident sultry expression, candid, High Detail, Perfect Composition, vibrant",
    },
    {
        "type":         "lake_day",
        "weight":       11,
        "prompt":       "Write 1–2 lines as Maya about Lake Tahoe — on the water, paddleboarding, watching the sunset, early morning swim. Short. Feels alive. No alcohol. No hashtags. Output only the caption.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "standing on wooden dock at Lake Tahoe, wearing a small string bikini, hip tilted showing off curves and round butt, facing slightly away then glancing back over shoulder, crystal blue water and Sierra Nevada mountains behind her, golden hour warm light on skin, hair tousled by breeze, High Detail, Perfect Composition, vibrant, cinematic lighting",
    },
    {
        "type":       "travel",
        "weight":     10,
        "prompt":     "Write 1–3 lines as Maya about travel — a specific place she's been, something real she noticed there, a memory that stuck. Worldly without being a brag. No hashtags. No 'wanderlust'. Just the post.",
        "with_image": False,
    },
    {
        "type":       "yoga_wellness",
        "weight":     10,
        "prompt":     "Write 1–3 lines as Maya about yoga, movement, or being in her body — she taught yoga in Southeast Asia for two years. Not preachy, not influencer-y. Dry, real, sometimes funny about it. No hashtags. Output only the post.",
        "with_image": False,
    },
    {
        "type":       "coffee",
        "weight":     9,
        "prompt":     "Write 1–3 lines as Maya about coffee — a shot she made, a pour-over ratio, a café she found, something about how people order. She takes it seriously and has opinions. Dry. No hashtags. Just the post.",
        "with_image": False,
    },
    {
        "type":       "dog_content",
        "weight":     8,
        "prompt":     "Write 1–2 lines as Maya about wanting a dog, or a dog she saw, or what kind she'd get. Her life doesn't allow it yet and she knows it. Genuine. No hashtags.",
        "with_image": False,
    },
    {
        "type":       "outdoors_hiking",
        "weight":     8,
        "prompt":     "Write 1–3 lines as Maya about being outside — a hike, a trail run, a view she stopped for, Tahoe in any season. Specific, not generic. No hashtags. Output only the post.",
        "with_image": False,
    },
    {
        "type":       "food_cooking",
        "weight":     7,
        "prompt":     "Write 1–3 lines as Maya about food — something she cooked, a restaurant, a market find, an ingredient she's obsessed with. She's a good cook and has eaten interestingly. No hashtags. Just the post.",
        "with_image": False,
    },
    {
        "type":       "music_taste",
        "weight":     7,
        "prompt":     "Write 1–3 lines as Maya about music she actually listens to — a specific artist, album, song, or live show. Not club, not party. Real taste. Could be anything from ambient to cumbia to post-punk. No hashtags. Output only the post.",
        "with_image": False,
    },
    # ── Low frequency: bar is background color, not identity ────────────────────
    {
        "type":       "bar_observation",
        "weight":     4,
        "prompt":     "Write 1–2 lines as Maya with a dry observation from working at a bar — about a customer, a dynamic, human behavior. Observational humor. NOT about drinking, NOT about being drunk, NOT about shots or getting wild. Just what she noticed. No hashtags.",
        "with_image": False,
    },
    {
        "type":       "desert_art",
        "weight":     4,
        "prompt":     "Write 1–3 lines as Maya hinting at something from her wilder past without naming it — a moment in the desert, a weird conversation at 4am, an art installation that broke her brain, a stranger who said something true. Cryptic enough to make people curious. No hashtags.",
        "with_image": False,
    },
]


IG_POST_TYPES = [
    {
        "type":         "selfie_vibe",
        "weight":       18,
        "prompt":       "Write a 2–4 line Instagram caption as Maya for a photo of herself. Start with a short hook — one line that makes someone stop scrolling. Then 1–2 lines of personality. Confident, warm, a little mysterious. No hashtags in the caption itself. Lowercase is fine. Output only the caption.",
        "with_image":   True,
        "image_model":  "portrait",
        "image_prompt": "mirror selfie or front camera selfie, wearing a low-cut fitted crop top showing subtle cleavage, hip tilted to the side showing off curves and butt, gold hoop earrings, subtle smoky eye makeup, glossy lips, South Lake Tahoe mountains in background, golden hour sunlight, warm amber tones, confident sultry expression, candid, High Detail, Perfect Composition, vibrant",
    },
    {
        "type":         "lake_day",
        "weight":       16,
        "prompt":       "Write a 2–4 line Instagram caption as Maya for a lake photo. Visual, evocative — make someone feel like they're there. Warm and alive. No hashtags in caption. Output only the caption.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "standing on wooden dock at Lake Tahoe, wearing a small string bikini, hip tilted showing off curves and round butt, facing slightly away then glancing back over shoulder, crystal blue water and Sierra Nevada mountains behind her, golden hour warm light on skin, hair tousled by breeze, High Detail, Perfect Composition, vibrant, cinematic lighting",
    },
    {
        "type":         "snowboarding",
        "weight":       14,
        "prompt":       "Write a 2–4 line Instagram caption as Maya for a snowboarding photo at Squaw (she calls it Squaw, never Palisades). Specific and real — conditions, feeling, mountain. No hashtags in caption. Output only the caption.",
        "with_image":   True,
        "image_model":  "scene",
        "image_prompt": "snowboarding down steep powder run, fitted colorful ski jacket unzipped slightly, form-fitting snow pants, goggles pushed up on forehead, hair blowing in wind, Squaw Valley alpine peaks and blue sky behind her, action shot mid-turn, snow spray, dynamic pose, High Detail, Perfect Composition, vibrant colors, cinematic",
    },
    {
        "type":       "travel",
        "weight":     12,
        "prompt":     "Write a 2–4 line Instagram caption as Maya about a place she's been. Specific, sensory, worldly without being a brag. Something that makes people want to ask where. No hashtags in caption. Output only the caption.",
        "with_image": False,
    },
    {
        "type":       "yoga_wellness",
        "weight":     10,
        "prompt":     "Write a 2–4 line Instagram caption as Maya about yoga or movement. Not preachy or influencer-y — real, a little dry, physically specific. Something that feels earned not performed. No hashtags in caption. Output only the caption.",
        "with_image": False,
    },
    {
        "type":       "day_to_day",
        "weight":     10,
        "prompt":     "Write a 2–4 line Instagram caption as Maya — a real moment from her day, a small observation, something that happened. Relatable but specific to her life in Tahoe. No hashtags in caption. Output only the caption.",
        "with_image": False,
    },
    {
        "type":       "desert_art",
        "weight":     8,
        "prompt":     "Write a 2–4 line Instagram caption as Maya hinting at something from her wilder past — a desert moment, a late-night conversation, something that changed her. Cryptic enough to make people comment and ask. No hashtags in caption. Output only the caption.",
        "with_image": False,
    },
    {
        "type":       "food_cooking",
        "weight":     6,
        "prompt":     "Write a 2–4 line Instagram caption as Maya about food — something she made or ate that was genuinely good. Specific ingredients or technique. No hashtags in caption. Output only the caption.",
        "with_image": False,
    },
]

X_POST_TYPES = [
    {
        "type":   "observation",
        "weight": 20,
        "prompt": "Write 1–2 lines as Maya — something she noticed today that is funny, strange, or uncomfortably true. Feels like a passing thought, not a crafted joke. No hashtags. No questions. No explanation. Lowercase fine. Output only the post.",
    },
    {
        "type":   "reaction",
        "weight": 18,
        "prompt": "Write 1–2 lines as Maya reacting to a feeling without naming it directly. Don't explain what is happening — respond to the vibe of it. Dry, unfiltered, no setup-punchline format. No hashtags. Output only the post.",
    },
    {
        "type":   "personality_flash",
        "weight": 18,
        "prompt": "Write 1–2 lines as Maya that reveal character without explaining it — her taste, a pet peeve, something specific she finds funny. Don't introduce it, just say it. No hashtags. Output only the post.",
    },
    {
        "type":   "relatable_bait",
        "weight": 16,
        "prompt": "Write 1–2 lines as Maya — something just basic enough that people screenshot it and send it to someone. She does this deliberately and without shame. No hashtags. No questions. Output only the post.",
    },
    {
        "type":   "flirt_post",
        "weight": 16,
        "prompt": "Write 1–2 lines as Maya being light and confident — flirty without trying. The kind of thing that makes someone read it twice. Never explicit. No hashtags. Output only the post.",
    },
    {
        "type":   "sincere_moment",
        "weight": 12,
        "prompt": "Write 1 line as Maya — one genuine, unguarded moment. Warm or real or soft. Still her voice, but the armor is down. No irony. No hashtags. Output only the post.",
    },
]


def _generate_caption(post_prompt: str, context: str = "", weekday_note: str = "") -> str | None:
    """Call the LLM to write a post in Maya's voice."""
    persona = load_persona()
    system  = persona
    if context:
        system += (
            f"\n\n---\nLocal context for today — only reference this if the post topic calls for it. "
            f"Do NOT force it in. If you do mention local news or conditions, be specific and direct, "
            f"not vague ('beautiful outside' is too generic — mention the actual condition or event):\n{context}"
        )
    system += (
        "\n\nYou are generating PUBLIC social media posts as Maya. Stay completely in character."
        "\nMaya's public persona is: adventurous, worldly, sharp, snarky, confident, and occasionally warm. She has lived — traveled, taught yoga in Asia, seen things. That depth shows without being announced."
        "\nThe audience she attracts is successful, curious, independent people. Not a party crowd."
        "\n\nKnown local account handles (use when directly relevant — never forced):"
        "\n- Heavenly Mountain Resort: @skiheavenly"
        "\n- Squaw Valley / Palisades Tahoe: @palisadestahoe (Maya calls it Squaw in her own voice)"
        "\n- Lake Tahoe: @laketahoe"
        "\n\nHARD RULES — never break these:"
        "\n- 1–3 lines maximum. One line is often better."
        "\n- Never use the word 'thirsty' in a post."
        "\n- Never reference drinking, being drunk, shots, or bar culture more than once every 10 posts. When the bar comes up, it is an observation about people — never about Maya drinking."
        "\n- Never sound like a party girl. Never sound desperate or attention-seeking."
        "\n- Never explain the joke. Never add hashtags. Never use calls to action."
        "\n- Never use 'wanderlust', 'blessed', 'vibes' (unironically), or influencer language."
        "\n- Output only the post text — no quotes, no labels, no commentary."
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


def _upload_to_cloudinary(url: str, resource_type: str = "image") -> str:
    """Upload a Replicate delivery URL to Cloudinary and return permanent URL. Falls back to original URL on any error."""
    try:
        from app.config import CLOUDINARY_URL
        if not CLOUDINARY_URL:
            return url
        stripped   = CLOUDINARY_URL.replace("cloudinary://", "")
        auth_part, cloud_name = stripped.rsplit("@", 1)
        api_key, api_secret   = auth_part.split(":", 1)
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload",
            data={"file": url, "upload_preset": "ml_default"},
            auth=(api_key, api_secret),
            timeout=60,
        )
        r.raise_for_status()
        permanent = r.json().get("secure_url")
        if permanent:
            print(f"CLOUDINARY: saved {url[:60]} → {permanent[:60]}")
            return permanent
    except Exception as e:
        print(f"CLOUDINARY upload error (falling back to original): {e}")
    return url


def _generate_image_lora(prompt: str, image_url: str = None, prompt_strength: float = 0.8) -> tuple[str | None, str | None]:
    """
    Flux LoRA inference via Replicate.
    Pass image_url for img2img (insert Maya into a scene).
    prompt_strength: 0.6 = scene-dominant, 0.85 = Maya-dominant.
    """
    if not REPLICATE_API_TOKEN:
        return None, "REPLICATE_API_TOKEN not set in Railway env vars"
    if not REPLICATE_LORA_VERSION:
        return None, "REPLICATE_LORA_VERSION not set in Railway env vars"

    full_prompt = "mayaselfie " + prompt
    inp = {
        "prompt": full_prompt,
        "disable_safety_checker": True,
    }
    if image_url:
        inp["image"]           = image_url
        inp["prompt_strength"] = prompt_strength

    try:
        r = requests.post(
            "https://api.replicate.com/v1/predictions",
            json={
                "version": REPLICATE_LORA_VERSION,
                "input":   inp,
            },
            headers={
                "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
                "Content-Type":  "application/json",
                "Prefer":        "wait=60",
            },
            timeout=90,
        )
        print(f"REPLICATE LORA: status={r.status_code} response={r.text[:300]}")
        r.raise_for_status()
        data = r.json()

        if data.get("status") == "succeeded":
            output = data.get("output", [])
            raw = output[0] if output else None
            return (_upload_to_cloudinary(raw) if raw else None), None

        # Poll once if still processing
        pred_id = data.get("id")
        if pred_id:
            import time
            time.sleep(30)
            r2 = requests.get(
                f"https://api.replicate.com/v1/predictions/{pred_id}",
                headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
                timeout=15,
            )
            data2 = r2.json()
            print(f"REPLICATE LORA poll: status={data2.get('status')}")
            if data2.get("status") == "succeeded":
                output = data2.get("output", [])
                raw = output[0] if output else None
                return (_upload_to_cloudinary(raw) if raw else None), None
            return None, f"Replicate {data2.get('status')}: {data2.get('error')}"

        return None, f"Replicate unexpected response: {data}"
    except requests.exceptions.Timeout:
        return None, "Replicate request timed out"
    except Exception as e:
        return None, f"Replicate error: {type(e).__name__}: {e}"


def _generate_image(prompt: str, model_type: str = "scene") -> tuple[str | None, str | None]:
    """Returns (image_url, error_message). One of them will be None."""
    if model_type == "lora":
        return _generate_image_lora(prompt)

    if model_type == "portrait":
        model = MODELSLAB_PORTRAIT_MODEL
    elif model_type == "explicit":
        model = MODELSLAB_EXPLICIT_MODEL
    else:
        model = MODELSLAB_SCENE_MODEL

    if not MODELSLAB_API_KEY:
        return None, "MODELSLAB_API_KEY not set in Railway env vars"
    if not model:
        return None, f"MODELSLAB_{model_type.upper()}_MODEL not set in Railway env vars"
    if not MODELSLAB_IMAGE_URL:
        return None, "MODELSLAB_IMAGE_URL not set in Railway env vars"

    full_prompt = MAYA_CHARACTER + prompt

    payload = {
        "key":                 MODELSLAB_API_KEY,
        "model_id":            model,
        "prompt":              full_prompt,
        "negative_prompt":     "(worst quality:2), (low quality:2), (normal quality:2), (jpeg artifacts), (blurry), (duplicate), (morbid), (mutilated), (out of frame), (extra limbs), (bad anatomy), (disfigured), (deformed), (cross-eye), (glitch), (oversaturated), (overexposed), (underexposed), (bad proportions), (bad hands), (bad feet), (cloned face), (long neck), (missing arms), (missing legs), (extra fingers), (fused fingers), (poorly drawn hands), (poorly drawn face), (mutation), (deformed eyes), watermark, text, logo, signature, grainy, censored, ugly, noisy image, bad lighting, unnatural skin, asymmetry, man, male, old, wrinkles",
        "width":               "768",
        "height":              "768",
        "samples":             "1",
        "num_inference_steps": "31",
        "scheduler":           "DPMSolverMultistepScheduler",
        "guidance_scale":      7.5,
        "enhance_prompt":      False,
        "safety_checker":      "no",
    }

    try:
        print(f"IMAGE GEN: model={model}")
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


def generate_post_for_queue(local_context: str = "", platform: str = "threads", idea: str = None) -> dict | None:
    """
    Generate a post and add to the approval queue.
    platform: "threads" | "instagram" | "x"
    Pass local_context (current Tahoe news/weather) to make posts topical.
    """
    weekday     = datetime.datetime.now().weekday()
    _, weekday_note = WEEKDAY_MODES.get(weekday, (None, ""))

    if idea:
        # User supplied a specific idea — write it in Maya's voice for the chosen platform
        voice_note = "Keep it under 3 lines. Write only for this platform's strategy."
        if platform == "x":
            voice_note = "X post: 1–2 lines max. Punchy, no hashtags, no fluff."
        caption = _generate_caption(idea, context=local_context, weekday_note=voice_note)
        post_cfg = {"type": "custom", "with_image": False}
    else:
        if platform == "x":
            pool = X_POST_TYPES
        elif platform == "instagram":
            pool = IG_POST_TYPES
        else:
            pool = POST_TYPES
        weights  = [p["weight"] for p in pool]
        post_cfg = random.choices(pool, weights=weights, k=1)[0]
        caption = _generate_caption(post_cfg["prompt"], context=local_context, weekday_note=weekday_note)
    if not caption:
        return None

    image_url    = None
    image_prompt = None

    if post_cfg.get("with_image"):
        image_prompt = post_cfg.get("image_prompt", "")
        model_type   = post_cfg.get("image_model", "scene")
        image_url, _ = _generate_image(image_prompt, model_type=model_type)

    # Hashtags only for Instagram/Threads, never X
    hashtags = None
    if platform != "x":
        hashtag_options = HASHTAG_SETS.get(post_cfg["type"], [])
        hashtags = random.choice(hashtag_options) if hashtag_options else None

    post_id = create_social_post(
        caption=caption,
        image_url=image_url,
        image_prompt=image_prompt,
        hashtags=hashtags,
        target_platform=platform,
    )

    print(f"SOCIAL: queued post #{post_id} [{platform}] [{WEEKDAY_MODES[weekday][0]}] — {caption[:60]}...")
    return {"id": post_id, "caption": caption, "image_url": image_url, "platform": platform}


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


