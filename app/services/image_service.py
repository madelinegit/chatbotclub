"""
Text card image generator for Maya's social posts.
Uses Pillow (free, no API) to create branded quote cards.
Falls back gracefully if fonts aren't available.
"""
import io
import os
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont

# Maya's brand colors
BG_COLOR      = (10, 10, 11)       # #0a0a0b
ACCENT_COLOR  = (201, 149, 106)    # #c9956a warm terracotta
TEXT_COLOR    = (240, 237, 232)    # #f0ede8
MUTED_COLOR   = (90, 88, 85)       # #5a5855

CARD_W = 1080
CARD_H = 1080

FONT_DIR = "static/fonts"


def _load_font(size: int, bold: bool = False):
    """Try to load a font, fall back to PIL default."""
    try:
        name = "Georgia Bold.ttf" if bold else "Georgia.ttf"
        path = os.path.join(FONT_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    # Try system fonts
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/times.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_text_card(caption: str) -> bytes | None:
    """
    Generate a 1080x1080 branded text card for a post caption.
    Returns PNG bytes or None on failure.
    """
    try:
        img  = Image.new("RGB", (CARD_W, CARD_H), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Subtle gradient overlay — draw horizontal bands
        for y in range(CARD_H):
            alpha = int(15 * (y / CARD_H))
            draw.line([(0, y), (CARD_W, y)], fill=(201, 149, 106, alpha))

        # Top accent line
        draw.rectangle([(80, 80), (200, 84)], fill=ACCENT_COLOR)

        # "maya" wordmark top left
        wordmark_font = _load_font(28)
        draw.text((80, 100), "maya", font=wordmark_font, fill=ACCENT_COLOR)

        # Main quote text — wrap to fit
        quote_font  = _load_font(52)
        max_chars   = 28
        wrapped     = textwrap.fill(caption, width=max_chars)
        lines       = wrapped.split("\n")

        # Center the text block vertically
        line_height = 68
        total_h     = len(lines) * line_height
        start_y     = (CARD_H - total_h) // 2 - 40

        for i, line in enumerate(lines):
            y = start_y + i * line_height
            # Shadow
            draw.text((82, y + 2), line, font=quote_font, fill=(0, 0, 0))
            # Text
            draw.text((80, y), line, font=quote_font, fill=TEXT_COLOR)

        # Bottom rule + site name
        draw.rectangle([(80, CARD_H - 100), (CARD_W - 80, CARD_H - 97)], fill=MUTED_COLOR)
        site_font = _load_font(24)
        draw.text((80, CARD_H - 88), "magicmaya.vip", font=site_font, fill=MUTED_COLOR)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    except Exception as e:
        print(f"IMAGE CARD ERROR: {e}")
        return None


def _notify_image(caption: str, image_url: str) -> None:
    """Fire-and-forget email with the image URL to NOTIFY_EMAIL."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from app.config import GMAIL_USER, GMAIL_APP_PASSWORD, NOTIFY_EMAIL

        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Maya post image ready"
        msg["From"]    = GMAIL_USER
        msg["To"]      = NOTIFY_EMAIL

        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0f0f10;color:#e0ddd8;padding:24px;border-radius:12px;">
          <div style="font-size:13px;color:#c9956a;letter-spacing:.1em;text-transform:uppercase;margin-bottom:16px;">Maya — New Post</div>
          <img src="{image_url}" style="width:100%;border-radius:8px;margin-bottom:16px;" />
          <div style="font-size:15px;line-height:1.6;color:#e0ddd8;margin-bottom:16px;">"{caption}"</div>
          <a href="{image_url}" style="color:#c9956a;font-size:13px;">View full image ↗</a>
          <div style="margin-top:24px;font-size:11px;color:#555;">magicmaya.vip</div>
        </div>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())

        print(f"EMAIL: image notification sent to {NOTIFY_EMAIL}")
    except Exception as e:
        print(f"EMAIL NOTIFY ERROR: {e}")


def upload_text_card(caption: str) -> str | None:
    """
    Generate a text card and upload it to Cloudinary.
    Returns a public URL or None if upload fails or CLOUDINARY_URL not set.
    """
    import base64
    from app.config import CLOUDINARY_URL

    if not CLOUDINARY_URL:
        print("CLOUDINARY: no CLOUDINARY_URL set, skipping image upload")
        return None

    card_bytes = generate_text_card(caption)
    if not card_bytes:
        return None

    try:
        # Parse cloudinary://api_key:api_secret@cloud_name
        stripped  = CLOUDINARY_URL.replace("cloudinary://", "")
        auth_part, cloud_name = stripped.rsplit("@", 1)
        api_key, api_secret   = auth_part.split(":", 1)

        encoded = base64.b64encode(card_bytes).decode("utf-8")
        data_uri = f"data:image/png;base64,{encoded}"

        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            data={"file": data_uri, "upload_preset": "ml_default"},
            auth=(api_key, api_secret),
            timeout=30,
        )
        r.raise_for_status()
        url = r.json().get("secure_url")
        if url:
            _notify_image(caption, url)
        return url
    except Exception as e:
        print(f"CLOUDINARY UPLOAD ERROR: {e}")
        return None
