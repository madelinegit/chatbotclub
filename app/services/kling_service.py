"""
Kling AI video generation service.
- image_to_video: takes an image URL + motion prompt → returns video URL
- text_to_video:  text prompt only → returns video URL
Uses HMAC-SHA256 JWT auth (no external JWT library needed).
"""
import base64
import hashlib
import hmac
import json
import time
import requests
from app.config import KLING_ACCESS_KEY, KLING_SECRET_KEY

KLING_API = "https://api.klingai.com"


def _make_jwt() -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(data, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

    now    = int(time.time())
    header = b64({"alg": "HS256", "typ": "JWT"})
    payload = b64({"iss": KLING_ACCESS_KEY, "exp": now + 1800, "nbf": now - 5})
    msg = f"{header}.{payload}"
    sig = base64.urlsafe_b64encode(
        hmac.new(KLING_SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{msg}.{sig}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_make_jwt()}",
        "Content-Type":  "application/json",
    }


def _poll(endpoint: str, task_id: str, max_wait: int = 300) -> str | None:
    """Poll until video is ready. Returns video URL or None."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(10)
        try:
            r = requests.get(f"{KLING_API}{endpoint}/{task_id}", headers=_headers(), timeout=15)
            if r.status_code == 429:
                print("KLING poll: rate limited, waiting 30s")
                time.sleep(30)
                continue
            r.raise_for_status()
        except Exception as e:
            print(f"KLING poll error: {e}")
            time.sleep(15)
            continue
        data   = r.json().get("data", {})
        status = data.get("task_status")
        print(f"KLING poll: status={status}")
        if status == "succeed":
            works = data.get("task_result", {}).get("videos", [])
            return works[0].get("url") if works else None
        if status == "failed":
            print(f"KLING task failed: {data.get('task_status_msg')}")
            return None
    return None


def image_to_video(image_url: str, prompt: str = "", duration: int = 5) -> tuple[str | None, str | None]:
    """
    Animate an image into a video.
    Returns (video_url, error_message).
    """
    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        return None, "KLING_ACCESS_KEY / KLING_SECRET_KEY not set in Railway"

    payload = {
        "model_name": "kling-v1",
        "image":      image_url,
        "duration":   str(duration),
        "mode":       "std",
    }
    if prompt:
        payload["prompt"] = prompt

    try:
        r = requests.post(
            f"{KLING_API}/v1/videos/image2video",
            json=payload, headers=_headers(), timeout=30,
        )
        print(f"KLING i2v create: status={r.status_code} body={r.text[:300]}")
        if r.status_code == 429:
            return None, "Kling rate limit hit — wait a minute and try again"
        r.raise_for_status()
        task_id = r.json().get("data", {}).get("task_id")
        if not task_id:
            return None, f"No task_id returned: {r.text[:200]}"

        video_url = _poll("/v1/videos/image2video", task_id)
        if video_url:
            return video_url, None
        return None, "Video generation timed out or failed"
    except Exception as e:
        return None, f"Kling error: {type(e).__name__}: {e}"


def text_to_video(prompt: str, duration: int = 5) -> tuple[str | None, str | None]:
    """
    Generate a video from a text prompt.
    Returns (video_url, error_message).
    """
    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        return None, "KLING_ACCESS_KEY / KLING_SECRET_KEY not set in Railway"

    try:
        r = requests.post(
            f"{KLING_API}/v1/videos/text2video",
            json={"model_name": "kling-v1", "prompt": prompt, "duration": str(duration), "mode": "std"},
            headers=_headers(), timeout=30,
        )
        print(f"KLING t2v create: status={r.status_code} body={r.text[:300]}")
        if r.status_code == 429:
            return None, "Kling rate limit hit — wait a minute and try again"
        r.raise_for_status()
        task_id = r.json().get("data", {}).get("task_id")
        if not task_id:
            return None, f"No task_id returned: {r.text[:200]}"

        video_url = _poll("/v1/videos/text2video", task_id)
        if video_url:
            return video_url, None
        return None, "Video generation timed out or failed"
    except Exception as e:
        return None, f"Kling error: {type(e).__name__}: {e}"
