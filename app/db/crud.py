import psycopg2.extras
from app.db.database import get_connection


def _cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(user_id: str, role: str, content: str) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (%s, %s, %s)",
        (user_id, role, content),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_recent_messages(user_id: str, limit: int = 10) -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        """
        SELECT role, content FROM messages
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return list(reversed([dict(r) for r in rows]))


def get_all_messages(user_id: str) -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT role, content, created_at FROM messages WHERE user_id = %s ORDER BY created_at ASC",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(user_id: str, email: str, initial_credits: int = 0) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "INSERT INTO users (id, email) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (user_id, email),
    )
    cur.execute(
        "INSERT INTO credits (user_id, balance) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (user_id, initial_credits),
    )
    cur.execute(
        "INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def set_age_verified(user_id: str) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("UPDATE users SET age_verified = 1 WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def is_age_verified(user_id: str) -> bool:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT age_verified FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return bool(row["age_verified"]) if row else False


def is_dev_user(user_id: str) -> bool:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT is_dev FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return bool(row["is_dev"]) if row else False


def set_dev_user(user_id: str, enabled: bool = True) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "UPDATE users SET is_dev = %s WHERE id = %s",
        (1 if enabled else 0, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# ── Profiles ──────────────────────────────────────────────────────────────────

def get_profile(user_id: str) -> dict | None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def update_profile(user_id: str, display_name: str = None, bio: str = None, avatar_url: str = None) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        """
        INSERT INTO user_profiles (user_id, display_name, bio, avatar_url, updated_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            display_name = COALESCE(EXCLUDED.display_name, user_profiles.display_name),
            bio          = COALESCE(EXCLUDED.bio,          user_profiles.bio),
            avatar_url   = COALESCE(EXCLUDED.avatar_url,   user_profiles.avatar_url),
            updated_at   = NOW()
        """,
        (user_id, display_name, bio, avatar_url),
    )
    conn.commit()
    cur.close()
    conn.close()


# ── Credits ───────────────────────────────────────────────────────────────────

def get_credit_balance(user_id: str) -> int:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT balance FROM credits WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["balance"] if row else 0


def add_credits(user_id: str, amount: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "UPDATE credits SET balance = balance + %s, updated_at = NOW() WHERE user_id = %s",
        (amount, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def deduct_credit(user_id: str) -> bool:
    """Deduct 1 credit atomically. Returns False if balance is 0."""
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT balance FROM credits WHERE user_id = %s FOR UPDATE",
        (user_id,),
    )
    row = cur.fetchone()
    if not row or row["balance"] < 1:
        cur.close()
        conn.close()
        return False
    cur.execute(
        "UPDATE credits SET balance = balance - 1, updated_at = NOW() WHERE user_id = %s",
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return True


# ── Transactions ──────────────────────────────────────────────────────────────

def log_transaction(user_id: str, amount_cents: int, credits_added: int, processor_ref: str = None) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        """
        INSERT INTO transactions (user_id, amount_cents, credits_added, processor_ref)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, amount_cents, credits_added, processor_ref),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_transactions(user_id: str) -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT * FROM transactions WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


# ── Blog Posts ────────────────────────────────────────────────────────────────

def get_published_blog_posts() -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT id, title, slug, excerpt, cover_image_url, credit_cost, published_at FROM blog_posts WHERE status = 'published' ORDER BY published_at DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_blog_post_by_slug(slug: str) -> dict | None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM blog_posts WHERE slug = %s", (slug,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_blog_post_by_id(post_id: int) -> dict | None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM blog_posts WHERE id = %s", (post_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_all_blog_posts() -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM blog_posts ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def create_blog_post(title: str, slug: str, excerpt: str, content: str,
                     cover_image_url: str = None, credit_cost: int = 5) -> int:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        """
        INSERT INTO blog_posts (title, slug, excerpt, content, cover_image_url, credit_cost)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (title, slug, excerpt, content, cover_image_url, credit_cost),
    )
    post_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return post_id


def update_blog_post(post_id: int, title: str = None, slug: str = None,
                     excerpt: str = None, content: str = None,
                     cover_image_url: str = None, credit_cost: int = None) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    fields, values = [], []
    if title           is not None: fields.append("title = %s");           values.append(title)
    if slug            is not None: fields.append("slug = %s");            values.append(slug)
    if excerpt         is not None: fields.append("excerpt = %s");         values.append(excerpt)
    if content         is not None: fields.append("content = %s");         values.append(content)
    if cover_image_url is not None: fields.append("cover_image_url = %s"); values.append(cover_image_url)
    if credit_cost     is not None: fields.append("credit_cost = %s");     values.append(credit_cost)
    if not fields:
        cur.close()
        conn.close()
        return
    fields.append("updated_at = NOW()")
    values.append(post_id)
    cur.execute(f"UPDATE blog_posts SET {', '.join(fields)} WHERE id = %s", values)
    conn.commit()
    cur.close()
    conn.close()


def publish_blog_post(post_id: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "UPDATE blog_posts SET status = 'published', published_at = NOW(), updated_at = NOW() WHERE id = %s",
        (post_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def unpublish_blog_post(post_id: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "UPDATE blog_posts SET status = 'draft', updated_at = NOW() WHERE id = %s",
        (post_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_blog_post(post_id: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("DELETE FROM blog_unlocks WHERE post_id = %s", (post_id,))
    cur.execute("DELETE FROM blog_posts WHERE id = %s", (post_id,))
    conn.commit()
    cur.close()
    conn.close()


def has_unlocked_blog_post(user_id: str, post_id: int) -> bool:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT 1 FROM blog_unlocks WHERE user_id = %s AND post_id = %s",
        (user_id, post_id),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None


def unlock_blog_post(user_id: str, post_id: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "INSERT INTO blog_unlocks (user_id, post_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (user_id, post_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# ── Social Posts ──────────────────────────────────────────────────────────────

def create_social_post(caption: str, image_url: str = None, image_prompt: str = None, scheduled_at: str = None) -> int:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        """
        INSERT INTO social_posts (caption, image_url, image_prompt, scheduled_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (caption, image_url, image_prompt, scheduled_at),
    )
    post_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return post_id


def get_pending_posts() -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM social_posts WHERE status = 'pending' ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_all_posts(limit: int = 50) -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM social_posts ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def approve_post(post_id: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("UPDATE social_posts SET status = 'approved' WHERE id = %s", (post_id,))
    conn.commit()
    cur.close()
    conn.close()


def reject_post(post_id: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("UPDATE social_posts SET status = 'rejected' WHERE id = %s", (post_id,))
    conn.commit()
    cur.close()
    conn.close()


def mark_post_posted(post_id: int, platform_post_id: str) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "UPDATE social_posts SET status = 'posted', post_id = %s, posted_at = NOW() WHERE id = %s",
        (platform_post_id, post_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def mark_post_failed(post_id: int) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute("UPDATE social_posts SET status = 'failed' WHERE id = %s", (post_id,))
    conn.commit()
    cur.close()
    conn.close()


# ── Social Comment Replies ────────────────────────────────────────────────────

def log_comment_reply(platform: str, comment_id: str, post_id: str,
                      reply_text: str, platform_reply_id: str = None) -> None:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        """
        INSERT INTO social_comment_replies
            (platform, comment_id, post_id, reply_text, platform_reply_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (platform, comment_id) DO NOTHING
        """,
        (platform, comment_id, post_id, reply_text, platform_reply_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def has_replied_to_comment(platform: str, comment_id: str) -> bool:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT 1 FROM social_comment_replies WHERE platform = %s AND comment_id = %s",
        (platform, comment_id),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None


def get_recent_comment_replies(limit: int = 50) -> list:
    conn = get_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT * FROM social_comment_replies ORDER BY replied_at DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]
