from app.db.crud import get_recent_messages, save_message


MAX_HISTORY = 10


def get_history(user_id: str) -> list[dict]:
    """Return the last MAX_HISTORY messages for a user as role/content dicts."""
    rows = get_recent_messages(user_id, limit=MAX_HISTORY)
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def add_message(user_id: str, role: str, content: str) -> None:
    """Persist a single message to the database."""
    if not content or not content.strip():
        return
    save_message(user_id=user_id, role=role, content=content)
