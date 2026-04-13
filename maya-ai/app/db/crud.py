from app.db.database import get_connection


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(user_id: str, role: str, content: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    conn.commit()
    conn.close()


def get_recent_messages(user_id: str, limit: int = 10) -> list:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT role, content FROM messages
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return list(reversed([dict(row) for row in rows]))


def get_all_messages(user_id: str) -> list:
    """Return full chat history for profile/history page."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content, created_at FROM messages WHERE user_id = ? ORDER BY created_at ASC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(user_id: str, email: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email) VALUES (?, ?)",
        (user_id, email),
    )
    conn.execute(
        "INSERT OR IGNORE INTO credits (user_id, balance) VALUES (?, 0)",
        (user_id,),
    )
    conn.execute(
        "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)",
        (user_id,),
    )
    conn.commit()
    conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_age_verified(user_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE users SET age_verified = 1 WHERE id = ?", (user_id,)
    )
    conn.commit()
    conn.close()


def is_age_verified(user_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT age_verified FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return bool(row["age_verified"]) if row else False


def is_dev_user(user_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT is_dev FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return bool(row["is_dev"]) if row else False


def set_dev_user(user_id: str, enabled: bool = True) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE users SET is_dev = ? WHERE id = ?", (1 if enabled else 0, user_id)
    )
    conn.commit()
    conn.close()


# ── Profiles ──────────────────────────────────────────────────────────────────

def get_profile(user_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_profile(user_id: str, display_name: str = None, bio: str = None, avatar_url: str = None) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO user_profiles (user_id, display_name, bio, avatar_url, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            display_name = COALESCE(excluded.display_name, display_name),
            bio          = COALESCE(excluded.bio, bio),
            avatar_url   = COALESCE(excluded.avatar_url, avatar_url),
            updated_at   = datetime('now')
        """,
        (user_id, display_name, bio, avatar_url),
    )
    conn.commit()
    conn.close()


# ── Credits ───────────────────────────────────────────────────────────────────

def get_credit_balance(user_id: str) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT balance FROM credits WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["balance"] if row else 0


def add_credits(user_id: str, amount: int) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE credits SET balance = balance + ?, updated_at = datetime('now')
        WHERE user_id = ?
        """,
        (amount, user_id),
    )
    conn.commit()
    conn.close()


def deduct_credit(user_id: str) -> bool:
    """Deduct 1 credit. Returns False if balance is 0."""
    conn = get_connection()
    row = conn.execute(
        "SELECT balance FROM credits WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not row or row["balance"] < 1:
        conn.close()
        return False

    conn.execute(
        """
        UPDATE credits SET balance = balance - 1, updated_at = datetime('now')
        WHERE user_id = ?
        """,
        (user_id,),
    )
    conn.commit()
    conn.close()
    return True


# ── Transactions ──────────────────────────────────────────────────────────────

def log_transaction(user_id: str, amount_cents: int, credits_added: int, processor_ref: str = None) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO transactions (user_id, amount_cents, credits_added, processor_ref)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, amount_cents, credits_added, processor_ref),
    )
    conn.commit()
    conn.close()


def get_transactions(user_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ── Blog Posts ────────────────────────────────────────────────────────────────

def get_published_blog_posts() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, slug, excerpt, cover_image_url, credit_cost, published_at FROM blog_posts WHERE status = 'published' ORDER BY published_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_blog_post_by_slug(slug: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM blog_posts WHERE slug = ?", (slug,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_blog_post_by_id(post_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM blog_posts WHERE id = ?", (post_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_blog_posts() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM blog_posts ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_blog_post(title: str, slug: str, excerpt: str, content: str,
                     cover_image_url: str = None, credit_cost: int = 5) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO blog_posts (title, slug, excerpt, content, cover_image_url, credit_cost)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (title, slug, excerpt, content, cover_image_url, credit_cost),
    )
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id


def update_blog_post(post_id: int, title: str = None, slug: str = None,
                     excerpt: str = None, content: str = None,
                     cover_image_url: str = None, credit_cost: int = None) -> None:
    conn = get_connection()
    # Build dynamic SET clause for only provided fields
    fields, values = [], []
    if title           is not None: fields.append("title = ?");           values.append(title)
    if slug            is not None: fields.append("slug = ?");            values.append(slug)
    if excerpt         is not None: fields.append("excerpt = ?");         values.append(excerpt)
    if content         is not None: fields.append("content = ?");         values.append(content)
    if cover_image_url is not None: fields.append("cover_image_url = ?"); values.append(cover_image_url)
    if credit_cost     is not None: fields.append("credit_cost = ?");     values.append(credit_cost)
    if not fields:
        conn.close()
        return
    fields.append("updated_at = datetime('now')")
    values.append(post_id)
    conn.execute(f"UPDATE blog_posts SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def publish_blog_post(post_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE blog_posts SET status = 'published', published_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
        (post_id,),
    )
    conn.commit()
    conn.close()


def unpublish_blog_post(post_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE blog_posts SET status = 'draft', updated_at = datetime('now') WHERE id = ?",
        (post_id,),
    )
    conn.commit()
    conn.close()


def delete_blog_post(post_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM blog_unlocks WHERE post_id = ?", (post_id,))
    conn.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()


def has_unlocked_blog_post(user_id: str, post_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM blog_unlocks WHERE user_id = ? AND post_id = ?", (user_id, post_id)
    ).fetchone()
    conn.close()
    return row is not None


def unlock_blog_post(user_id: str, post_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO blog_unlocks (user_id, post_id) VALUES (?, ?)",
        (user_id, post_id),
    )
    conn.commit()
    conn.close()


# ── Social Posts ──────────────────────────────────────────────────────────────

def create_social_post(caption: str, image_url: str = None, image_prompt: str = None, scheduled_at: str = None) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO social_posts (caption, image_url, image_prompt, scheduled_at)
        VALUES (?, ?, ?, ?)
        """,
        (caption, image_url, image_prompt, scheduled_at),
    )
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id


def get_pending_posts() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM social_posts WHERE status = 'pending' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_posts(limit: int = 50) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM social_posts ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def approve_post(post_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE social_posts SET status = 'approved' WHERE id = ?", (post_id,)
    )
    conn.commit()
    conn.close()


def reject_post(post_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE social_posts SET status = 'rejected' WHERE id = ?", (post_id,)
    )
    conn.commit()
    conn.close()


def mark_post_posted(post_id: int, platform_post_id: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE social_posts
        SET status = 'posted', post_id = ?, posted_at = datetime('now')
        WHERE id = ?
        """,
        (platform_post_id, post_id),
    )
    conn.commit()
    conn.close()


def mark_post_failed(post_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE social_posts SET status = 'failed' WHERE id = ?", (post_id,)
    )
    conn.commit()
    conn.close()
