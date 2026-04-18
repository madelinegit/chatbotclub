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


def _http_error(r: requests.Response, context: str) -> str:
    """Build a detailed error string from a non-2xx response."""
    try:
        body = r.json()
    except Exception:
        body = r.text[:500]
    return (
        f"KLING {context} HTTP {r.status_code} {r.reason} | "
        f"url={r.url} | body={body}"
    )


def _poll(endpoint: str, task_id: str, max_wait: int = 300) -> tuple[str | None, str | None]:
    """Poll until video is ready. Returns (video_url, error)."""
    deadline = time.time() + max_wait
    attempts = 0
    while time.time() < deadline:
        time.sleep(10)
        attempts += 1
        try:
            r = requests.get(
                f"{KLING_API}{endpoint}/{task_id}",
                headers=_headers(), timeout=15,
            )
            if r.status_code == 429:
                print(f"KLING poll attempt {attempts}: 429 rate-limited, sleeping 30s | body={r.text[:200]}")
                time.sleep(30)
                continue
            if not r.ok:
                err = _http_error(r, f"poll attempt {attempts}")
                print(err)
                time.sleep(15)
                continue
        except requests.exceptions.Timeout:
            print(f"KLING poll attempt {attempts}: GET timeout after 15s, retrying")
            continue
        except Exception as e:
            print(f"KLING poll attempt {attempts}: {type(e).__name__}: {e}")
            time.sleep(15)
            continue

        data   = r.json().get("data", {})
        status = data.get("task_status")
        msg    = data.get("task_status_msg", "")
        print(f"KLING poll attempt {attempts}: task_id={task_id} status={status} msg={msg!r}")

        if status == "succeed":
            works = data.get("task_result", {}).get("videos", [])
            if works:
                return works[0].get("url"), None
            return None, f"KLING task succeeded but videos list is empty: {data}"
        if status == "failed":
            return None, f"KLING task failed: status_msg={msg!r} full_data={data}"

    elapsed = int(max_wait)
    return None, f"KLING poll timed out after {elapsed}s / {attempts} attempts — task_id={task_id} endpoint={endpoint}"


def image_to_video(image_url: str, prompt: str = "", duration: int = 5) -> tuple[str | None, str | None]:
    """
    Animate an image into a video.
    Returns (video_url, error_message).
    """
    if not KLING_ACCESS_KEY:
        return None, "KLING_ACCESS_KEY not set in Railway env vars"
    if not KLING_SECRET_KEY:
        return None, "KLING_SECRET_KEY not set in Railway env vars"

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
        print(f"KLING i2v create: status={r.status_code} body={r.text[:400]}")
        if not r.ok:
            return None, _http_error(r, "i2v create")
        task_id = r.json().get("data", {}).get("task_id")
        if not task_id:
            return None, f"KLING i2v: no task_id in response — full body={r.text[:300]}"

        return _poll("/v1/videos/image2video", task_id)

    except requests.exceptions.Timeout:
        return None, "KLING i2v create: POST timed out after 30s (Kling API may be slow)"
    except Exception as e:
        return None, f"KLING i2v create: {type(e).__name__}: {e}"


def text_to_video(prompt: str, duration: int = 5) -> tuple[str | None, str | None]:
    """
    Generate a video from a text prompt.
    Returns (video_url, error_message).
    """
    if not KLING_ACCESS_KEY:
        return None, "KLING_ACCESS_KEY not set in Railway env vars"
    if not KLING_SECRET_KEY:
        return None, "KLING_SECRET_KEY not set in Railway env vars"

    try:
        r = requests.post(
            f"{KLING_API}/v1/videos/text2video",
            json={"model_name": "kling-v1", "prompt": prompt, "duration": str(duration), "mode": "std"},
            headers=_headers(), timeout=30,
        )
        print(f"KLING t2v create: status={r.status_code} body={r.text[:400]}")
        if not r.ok:
            return None, _http_error(r, "t2v create")
        task_id = r.json().get("data", {}).get("task_id")
        if not task_id:
            return None, f"KLING t2v: no task_id in response — full body={r.text[:300]}"

        return _poll("/v1/videos/text2video", task_id)

    except requests.exceptions.Timeout:
        return None, "KLING t2v create: POST timed out after 30s (Kling API may be slow)"
    except Exception as e:
        return None, f"KLING t2v create: {type(e).__name__}: {e}"
