import sqlite3
from app.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they don't exist. Called once on startup."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           TEXT PRIMARY KEY,
            email        TEXT UNIQUE NOT NULL,
            created_at   TEXT DEFAULT (datetime('now')),
            is_active    INTEGER DEFAULT 1,
            age_verified INTEGER DEFAULT 0,
            is_dev       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id      TEXT PRIMARY KEY,
            display_name TEXT,
            bio          TEXT,
            avatar_url   TEXT,
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            role       TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS credits (
            user_id    TEXT PRIMARY KEY,
            balance    INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        TEXT NOT NULL,
            amount_cents   INTEGER NOT NULL,
            credits_added  INTEGER NOT NULL,
            processor_ref  TEXT,
            created_at     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS social_posts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            platform     TEXT NOT NULL DEFAULT 'twitter',
            caption      TEXT NOT NULL,
            image_url    TEXT,
            image_prompt TEXT,
            status       TEXT NOT NULL DEFAULT 'pending'
                         CHECK(status IN ('pending', 'approved', 'rejected', 'posted', 'failed')),
            post_id      TEXT,
            scheduled_at TEXT,
            posted_at    TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS blog_posts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT NOT NULL,
            slug             TEXT UNIQUE NOT NULL,
            excerpt          TEXT NOT NULL,
            content          TEXT NOT NULL,
            cover_image_url  TEXT,
            credit_cost      INTEGER NOT NULL DEFAULT 5,
            status           TEXT NOT NULL DEFAULT 'draft'
                             CHECK(status IN ('draft', 'published')),
            published_at     TEXT,
            created_at       TEXT DEFAULT (datetime('now')),
            updated_at       TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS blog_unlocks (
            user_id    TEXT NOT NULL,
            post_id    INTEGER NOT NULL,
            unlocked_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES blog_posts(id)
        );
    """)

    conn.commit()

    # Migration: add is_dev column to existing DBs that predate it
    existing = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "is_dev" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN is_dev INTEGER DEFAULT 0")
        conn.commit()

    conn.close()
    print("DB initialized.")
