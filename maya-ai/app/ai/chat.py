import requests
from app.config import MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL
from app.ai.memory import get_history, add_message
from app.ai.persona import load_persona
from app.ai.image import generate_image
from app.db.crud import get_profile
from app.services.local_context_service import inject_context_into_chat


IMAGE_TRIGGERS = [
    "show me you", "show me a pic", "show me a photo",
    "show me a picture", "show me what you look like",
    "show me yourself", "let me see you", "can i see you",
    "send me a pic", "send me a photo", "send me a picture",
    "send a pic", "send a photo", "send a picture",
    "drop a pic", "drop a photo", "drop a picture",
    "take a pic", "take a photo", "take a picture",
    "pic of you", "photo of you", "picture of you",
    "what do you look like", "show yourself",
    "post a pic", "post a photo", "post a picture",
    "snap a pic", "snap a photo", "snap a picture",
    "got a pic", "got a photo", "got any pics", "got any photos",
    "see you", "see a pic", "see a photo", "see a picture",
]


def _build_image_prompt(message: str) -> str:
    filler = [
        "show me", "send me", "a pic of", "a photo of",
        "a picture of", "can i see", "let me see",
    ]
    prompt = message.lower()
    for phrase in filler:
        prompt = prompt.replace(phrase, "")
    prompt = prompt.strip()
    if len(prompt) < 5:
        prompt = "Maya, beautiful woman, natural lighting, photorealistic"
    return prompt


def _build_user_context(user_id: str) -> str:
    profile = get_profile(user_id)
    if not profile:
        return ""
    parts = []
    if profile.get("display_name"):
        parts.append(f"The person you're talking to goes by: {profile['display_name']}.")
    if profile.get("bio"):
        parts.append(f"Here's what they've shared about themselves: {profile['bio']}")
    if not parts:
        return ""
    return "\n\n---\n" + " ".join(parts) + "\nUse this naturally — don't recite it back, just know it."


def generate_reply(user_id: str, message: str) -> str:
    lowered = message.lower()

    # Image request
    if any(phrase in lowered for phrase in IMAGE_TRIGGERS):
        image_prompt = _build_image_prompt(message)
        image_url    = generate_image(image_prompt)
        if image_url:
            reply = f"[IMAGE]{image_url}[/IMAGE]"
        else:
            reply = "I tried to send you something but it didn't go through. Try again."
        add_message(user_id, "user", message)
        add_message(user_id, "assistant", reply)
        return reply

    # Build system prompt: persona + user profile + local context if relevant
    persona       = load_persona()
    user_context  = _build_user_context(user_id)
    system_prompt = persona + user_context
    system_prompt = inject_context_into_chat(user_id, message, system_prompt)

    history  = get_history(user_id)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    payload = {"model": MODELSLAB_MODEL, "messages": messages}
    headers = {
        "Authorization": f"Bearer {MODELSLAB_API_KEY}",
        "Content-Type":  "application/json",
    }

    try:
        r = requests.post(MODELSLAB_API_URL, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"CHAT API ERROR: {e}")
        return "something went wrong on my end. give me a sec."

    print("MODELSLAB RAW:", data)

    if "error" in data:
        print("MODEL ERROR:", data)
        return "having some trouble right now. try again in a minute."

    if "choices" in data:
        reply = data["choices"][0]["message"]["content"]
    elif "output" in data:
        reply = data["output"][0]
    else:
        reply = str(data)

    add_message(user_id, "user", message)
    add_message(user_id, "assistant", reply)

    return reply
