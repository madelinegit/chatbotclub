import psycopg2
import psycopg2.extras
from app.config import DATABASE_URL


def get_connection() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db() -> None:
    """Create all tables if they don't exist. Called once on startup."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id           TEXT PRIMARY KEY,
            email        TEXT UNIQUE NOT NULL,
            created_at   TIMESTAMPTZ DEFAULT NOW(),
            is_active    INTEGER DEFAULT 1,
            age_verified INTEGER DEFAULT 0,
            is_dev       INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id      TEXT PRIMARY KEY,
            display_name TEXT,
            bio          TEXT,
            avatar_url   TEXT,
            updated_at   TIMESTAMPTZ DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         BIGSERIAL PRIMARY KEY,
            user_id    TEXT NOT NULL,
            role       TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content    TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS credits (
            user_id    TEXT PRIMARY KEY,
            balance    INTEGER DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id             BIGSERIAL PRIMARY KEY,
            user_id        TEXT NOT NULL,
            amount_cents   INTEGER NOT NULL,
            credits_added  INTEGER NOT NULL,
            processor_ref  TEXT,
            created_at     TIMESTAMPTZ DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS social_posts (
            id           BIGSERIAL PRIMARY KEY,
            platform     TEXT NOT NULL DEFAULT 'twitter',
            caption      TEXT NOT NULL,
            image_url    TEXT,
            image_prompt TEXT,
            status       TEXT NOT NULL DEFAULT 'pending'
                         CHECK(status IN ('pending', 'approved', 'rejected', 'posted', 'failed')),
            post_id      TEXT,
            scheduled_at TIMESTAMPTZ,
            posted_at    TIMESTAMPTZ,
            created_at   TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blog_posts (
            id               BIGSERIAL PRIMARY KEY,
            title            TEXT NOT NULL,
            slug             TEXT UNIQUE NOT NULL,
            excerpt          TEXT NOT NULL,
            content          TEXT NOT NULL,
            cover_image_url  TEXT,
            credit_cost      INTEGER NOT NULL DEFAULT 5,
            status           TEXT NOT NULL DEFAULT 'draft'
                             CHECK(status IN ('draft', 'published')),
            published_at     TIMESTAMPTZ,
            created_at       TIMESTAMPTZ DEFAULT NOW(),
            updated_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blog_unlocks (
            user_id     TEXT NOT NULL,
            post_id     BIGINT NOT NULL,
            unlocked_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES blog_posts(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS social_comment_replies (
            id                BIGSERIAL PRIMARY KEY,
            platform          TEXT NOT NULL DEFAULT 'threads',
            comment_id        TEXT NOT NULL,
            post_id           TEXT,
            reply_text        TEXT NOT NULL,
            platform_reply_id TEXT,
            replied_at        TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(platform, comment_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_tokens (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id         BIGSERIAL PRIMARY KEY,
            endpoint   TEXT UNIQUE NOT NULL,
            p256dh     TEXT NOT NULL,
            auth       TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Safe migrations
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_dev INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
    cur.execute("ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS hashtags TEXT")
    cur.execute("ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS target_platform TEXT DEFAULT 'threads'")

    conn.commit()
    cur.close()
    conn.close()
    print("DB initialized.")
