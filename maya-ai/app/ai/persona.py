from app.config import PERSONA_FILE

_persona_cache: str | None = None


def load_persona() -> str:
    global _persona_cache
    if _persona_cache is None:
        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            _persona_cache = f.read()
    return _persona_cache
