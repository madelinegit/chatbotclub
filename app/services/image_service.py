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


def upload_text_card(caption: str) -> str | None:
    """
    Generate a text card and upload it to a free image host (imgbb or similar).
    Returns a public URL or None.
    Returns None if IMGBB_API_KEY is not set — image posting skipped.
    """
    import base64
    from app.config import IMGBB_API_KEY

    card_bytes = generate_text_card(caption)
    if not card_bytes:
        return None

    if not IMGBB_API_KEY:
        # Save locally as fallback (won't work for Threads which needs a public URL)
        path = f"static/generated_cards/{abs(hash(caption))}.png"
        os.makedirs("static/generated_cards", exist_ok=True)
        with open(path, "wb") as f:
            f.write(card_bytes)
        return None

    try:
        encoded = base64.b64encode(card_bytes).decode("utf-8")
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": encoded},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["data"]["url"]
    except Exception as e:
        print(f"IMGBB UPLOAD ERROR: {e}")
        return None
