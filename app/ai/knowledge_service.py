"""
Knowledge injection for astrology and tarot.
Detects relevant keywords in the user's message and injects
the corresponding reference data into the system prompt.
"""
import json
import os
import re

_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

def _load(filename: str) -> dict:
    path = os.path.join(_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

_astro = None
_tarot = None

def _get_astro() -> dict:
    global _astro
    if _astro is None:
        _astro = _load("astrology.json")
    return _astro

def _get_tarot() -> dict:
    global _tarot
    if _tarot is None:
        _tarot = _load("tarot.json")
    return _tarot


# ── Astrology detection ────────────────────────────────────────────────────────

_SIGNS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
          "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]

_PLANETS = ["sun", "moon", "mercury", "venus", "mars", "jupiter",
            "saturn", "uranus", "neptune", "pluto", "chiron",
            "north node", "south node"]

_ASPECTS = ["conjunction", "sextile", "square", "trine", "opposition", "quincunx"]

_SPECIAL = {
    "mercury retrograde": "mercury_retrograde",
    "saturn return":      "saturn_return",
    "rising":             "rising_ascendant",
    "ascendant":          "rising_ascendant",
    "midheaven":          "midheaven",
    "stellium":           "stellium",
    "synastry":           "synastry",
}

_HOUSE_RE = re.compile(
    r'\b(\d{1,2})(?:st|nd|rd|th)?\s+house\b|'
    r'\bhouse\s+(?:of\s+)?(\d{1,2})\b',
    re.IGNORECASE
)

_TAROT_TRIGGERS = [
    "tarot", "reading", "pull a card", "pull the", "card for me",
    "what does the", "what card", "spread",
]

_MAJOR_NAMES = list(_get_tarot()["major_arcana"].keys()) if False else []  # lazy loaded

def _detect_astrology(text: str) -> list[tuple[str, str, dict]]:
    """Return list of (category, key, data) for matched astrology topics. Max 3."""
    lowered = text.lower()
    hits = []

    for sign in _SIGNS:
        if sign in lowered and len(hits) < 3:
            hits.append(("sign", sign, _get_astro()["signs"][sign]))

    for planet in _PLANETS:
        if planet in lowered and len(hits) < 3:
            hits.append(("planet", planet, _get_astro()["planets"][planet]))

    for aspect in _ASPECTS:
        if aspect in lowered and len(hits) < 3:
            hits.append(("aspect", aspect, _get_astro()["aspects"][aspect]))

    for phrase, key in _SPECIAL.items():
        if phrase in lowered and len(hits) < 3:
            hits.append(("special", key, _get_astro()["special_topics"][key]))

    house_match = _HOUSE_RE.search(lowered)
    if house_match and len(hits) < 3:
        num = house_match.group(1) or house_match.group(2)
        if num and num in _get_astro()["houses"]:
            hits.append(("house", num, _get_astro()["houses"][num]))

    return hits


def _detect_tarot(text: str) -> list[tuple[str, str, dict]]:
    """Return list of (suit_or_major, card_name, data) for matched tarot cards. Max 3."""
    lowered = text.lower()
    hits = []
    tarot = _get_tarot()

    # Check major arcana
    for card_name, data in tarot["major_arcana"].items():
        if card_name in lowered and len(hits) < 3:
            hits.append(("major", card_name, data))

    # Check minor arcana
    for suit, suit_data in tarot["minor_arcana"].items():
        for card_name, data in suit_data["cards"].items():
            if card_name in lowered and len(hits) < 3:
                hits.append((suit, card_name, data))

    return hits


def _format_astro_hit(category: str, key: str, data: dict) -> str:
    if category == "sign":
        return (
            f"[{key.title()} — {data['element']} {data['modality']}, ruled by {data['ruler']}]\n"
            f"{data['meaning']}"
        )
    elif category == "planet":
        return f"[{key.title()}]\n{data['meaning']}"
    elif category == "aspect":
        return f"[{key.title()} ({data['orb']})]\n{data['meaning']}"
    elif category == "house":
        return f"[{data['name']} — House {key}]\n{data['meaning']}"
    elif category == "special":
        return f"[{key.replace('_', ' ').title()}]\n{data['meaning']}"
    return ""


def _format_tarot_hit(suit: str, card_name: str, data: dict) -> str:
    section = "Major Arcana" if suit == "major" else f"{suit.title()} ({_get_tarot()['minor_arcana'][suit]['themes']})"
    return (
        f"[{card_name.title()} — {section}]\n"
        f"Upright: {data['upright']}\n"
        f"Reversed: {data['reversed']}"
    )


def get_knowledge_context(message: str) -> str:
    """
    Given a user message, return a knowledge injection string
    to append to the system prompt. Empty string if nothing relevant.
    """
    lowered = message.lower()
    sections = []

    astro_hits = _detect_astrology(lowered)
    if astro_hits:
        formatted = [_format_astro_hit(c, k, d) for c, k, d in astro_hits]
        sections.append(
            "ASTROLOGY REFERENCE (use this knowledge naturally — speak as Maya, not as a textbook):\n"
            + "\n\n".join(formatted)
        )

    is_tarot = any(t in lowered for t in _TAROT_TRIGGERS)
    tarot_hits = _detect_tarot(lowered)
    if is_tarot or tarot_hits:
        if tarot_hits:
            formatted = [_format_tarot_hit(s, n, d) for s, n, d in tarot_hits]
            sections.append(
                "TAROT REFERENCE (speak as Maya reading for this person — be specific, not generic):\n"
                + "\n\n".join(formatted)
            )
        else:
            sections.append(
                "TAROT REFERENCE: The user is asking about tarot. "
                "Offer to do a reading — pull 1–3 cards conceptually and interpret them for their situation."
            )

    if not sections:
        return ""

    return "\n\n---\n" + "\n\n".join(sections)
