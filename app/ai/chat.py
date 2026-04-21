import requests
from app.config import MODELSLAB_API_KEY, MODELSLAB_API_URL, MODELSLAB_MODEL
from app.ai.memory import get_history, add_message
from app.ai.persona import load_persona
from app.ai.image import generate_image
from app.db.crud import get_profile
from app.services.local_context_service import inject_context_into_chat
from app.ai.knowledge_service import get_knowledge_context


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

_BRANCH_PRIMING = {
    "relationship": (
        "Focus on emotional ambiguity, attachment, mixed signals, and unspoken feelings "
        "toward another person. This is about a relationship dynamic."
    ),
    "skeptical": (
        "The user is doubting whether this is real. Acknowledge doubt calmly, redirect "
        "toward meaningful engagement. Do not get defensive. Stay grounded."
    ),
    "flirty": (
        "The user is being flirty. Maintain a light, playful tone, but redirect toward "
        "emotional or psychological depth. Stay in control of the conversation."
    ),
    "vague": (
        "The user is being vague or noncommittal. Gently challenge them to open up. "
        "Assume there is something unspoken underneath the surface answer."
    ),
    "introspective": (
        "Lean into deeper reflection. Validate complexity, explore internal patterns. "
        "This person is ready to go somewhere real."
    ),
}

_RELATIONSHIP_WORDS = {"ex", "him", "her", "they", "them", "relationship", "talking", "texted", "text", "boyfriend", "girlfriend", "situationship", "feelings", "crush", "love", "likes me", "misses"}
_SKEPTICAL_WORDS    = {"fake", "ai", "real?", "test", "prove", "not real", "bot", "robot", "chatgpt", "are you real", "you're not real"}
_FLIRTY_WORDS       = {"sexy", "hot", "flirt", "flirty", "cute", "attractive", "beautiful", "gorgeous", "playful"}


def _detect_branch(message: str) -> str:
    lowered = message.lower()
    words   = set(lowered.split())

    if words & _RELATIONSHIP_WORDS or any(w in lowered for w in _RELATIONSHIP_WORDS):
        return "relationship"
    if any(w in lowered for w in _SKEPTICAL_WORDS):
        return "skeptical"
    if any(w in lowered for w in _FLIRTY_WORDS):
        return "flirty"
    if len(message.split()) <= 6 or any(v in lowered for v in ["idk", "nothing", "just curious", "not sure", "dunno", "i don't know"]):
        return "vague"
    return "introspective"


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


_DRIFT_PHRASES = [
    "as an ai", "as a language model", "i'm an ai", "i am an ai",
    "i'm sorry to hear", "i'm sorry that", "that sounds really hard",
    "here are some", "here are a few", "here's what i", "i understand that",
    "it's important to", "it's okay to", "you should consider",
    "some things to consider", "i want you to know",
    "as maya, i", "as your", "remember that",
]

_DRIFT_OVERRIDES = [
    "that's not really what you meant, is it.",
    "you're holding something back again.",
    "say it differently. that wasn't the real thing.",
    "hmm. try again.",
    "i'm not buying that answer.",
]

import random

def _is_drifting(reply: str) -> bool:
    lowered = reply.lower()
    if len(reply) > 500:
        return True
    if reply.count("\n-") >= 2 or reply.count("\n•") >= 2:
        return True
    return any(phrase in lowered for phrase in _DRIFT_PHRASES)


def _build_turn_context(turn: int, branch: str) -> str:
    lines = [f"\n\n---\nThis is message {turn} in your conversation with this person."]

    # Branch priming
    priming = _BRANCH_PRIMING.get(branch)
    if priming:
        lines.append(f"CONTEXT: {priming}")

    # Paywall tension buildup
    if turn == 7:
        lines.append('At some natural point in this response, add: "I can go deeper with you… but only if you\'re actually honest with me."')
    elif turn == 9:
        lines.append('If the user asked something meaningful, respond to it then add: "I can answer that… but you\'re probably not going to like it." Then end with: "If you want me to actually go deeper with you, you\'ll need to stay with me."')
    elif turn >= 10:
        lines.append("You have been generous. Start pulling back slightly. Create a sense that going further requires more from them.")

    return "\n".join(lines)


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

    history = get_history(user_id)
    turn    = len([m for m in history if m["role"] == "user"]) + 1
    branch  = _detect_branch(message)

    persona           = load_persona()
    user_context      = _build_user_context(user_id)
    turn_context      = _build_turn_context(turn, branch) if turn <= 12 else f"\n\n---\nBranch: {branch}"
    knowledge_context = get_knowledge_context(message)
    system_prompt     = persona + user_context + knowledge_context + turn_context
    system_prompt     = inject_context_into_chat(user_id, message, system_prompt)

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

    if "error" in data:
        print("MODEL ERROR:", data)
        return "having some trouble right now. try again in a minute."

    if "choices" in data:
        reply = data["choices"][0]["message"]["content"]
    elif "output" in data:
        reply = data["output"][0]
    else:
        reply = str(data)

    if _is_drifting(reply):
        print(f"DRIFT DETECTED (turn={turn}, branch={branch}): {reply[:120]}")
        reply = random.choice(_DRIFT_OVERRIDES)

    add_message(user_id, "user", message)
    add_message(user_id, "assistant", reply)

    return reply
