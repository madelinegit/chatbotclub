"""Web Push notification service (VAPID). Keys stored in app_tokens table."""
import json
from app.db.database import get_connection


def _get_token(key: str) -> str | None:
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT value FROM app_tokens WHERE key = %s", (key,))
        row = cur.fetchone()
        cur.close(); conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _set_token(key: str, value: str) -> None:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO app_tokens (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """, (key, value))
    conn.commit()
    cur.close(); conn.close()


def generate_vapid_keys() -> dict:
    """Generate VAPID key pair and store in DB. No-op if already generated."""
    existing = _get_token("VAPID_PUBLIC_KEY")
    if existing:
        return {"public_key": existing, "generated": False}

    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    import base64

    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).decode().rstrip("=")

    _set_token("VAPID_PRIVATE_KEY", priv_pem)
    _set_token("VAPID_PUBLIC_KEY",  pub_b64)
    return {"public_key": pub_b64, "generated": True}


def get_vapid_public_key() -> str | None:
    return _get_token("VAPID_PUBLIC_KEY")


def save_subscription(endpoint: str, p256dh: str, auth: str) -> None:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO push_subscriptions (endpoint, p256dh, auth) VALUES (%s, %s, %s)
        ON CONFLICT (endpoint) DO UPDATE SET p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth
    """, (endpoint, p256dh, auth))
    conn.commit()
    cur.close(); conn.close()


def delete_subscription(endpoint: str) -> None:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM push_subscriptions WHERE endpoint = %s", (endpoint,))
    conn.commit()
    cur.close(); conn.close()


def _get_subscriptions() -> list:
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions")
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [{"endpoint": r[0], "p256dh": r[1], "auth": r[2]} for r in rows]
    except Exception as e:
        print(f"PUSH: subscription fetch error: {e}")
        return []


def send_push(title: str, body: str, url: str = "/admin/app", tag: str = "maya-admin") -> int:
    """Send push to all registered devices. Returns count sent."""
    private_key = _get_token("VAPID_PRIVATE_KEY")
    if not private_key:
        print("PUSH: no VAPID keys — visit /admin/app/setup-vapid first")
        return 0

    subs = _get_subscriptions()
    if not subs:
        print("PUSH: no subscriptions registered")
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("PUSH: pywebpush not installed")
        return 0

    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    sent, dead = 0, []

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": "mailto:mgalldev@gmail.com"},
                content_encoding="aes128gcm",
            )
            sent += 1
        except WebPushException as ex:
            print(f"PUSH ERROR: {ex}")
            if ex.response and ex.response.status_code in (404, 410):
                dead.append(sub["endpoint"])
        except Exception as ex:
            print(f"PUSH ERROR: {ex}")

    for ep in dead:
        delete_subscription(ep)

    print(f"PUSH: sent {sent}/{len(subs)}")
    return sent
