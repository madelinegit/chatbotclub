"""
Video generation via Replicate.
- image_to_video: animates an image with an optional motion prompt
- text_to_video:  generates video from text prompt only
Uses minimax/video-01 which handles both modes.
"""
import os
import replicate
from app.config import REPLICATE_API_TOKEN

# minimax/video-01 — good quality, supports image+text and text-only
IMAGE_TO_VIDEO_MODEL = "minimax/video-01"
TEXT_TO_VIDEO_MODEL  = "minimax/video-01"


def _check_token() -> str | None:
    if not REPLICATE_API_TOKEN:
        return "REPLICATE_API_TOKEN not set in Railway env vars"
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
    return None


def image_to_video(image_url: str, prompt: str = "", duration: int = 5) -> tuple[str | None, str | None]:
    """
    Animate an image into a video.
    Returns (video_url, error_message).
    """
    err = _check_token()
    if err:
        return None, err
    if not image_url:
        return None, "image_to_video: image_url is required"

    try:
        inp = {
            "first_frame_image": image_url,
            "prompt":     prompt or "cinematic motion, smooth camera movement",
            "model":      "MiniMax-Hailuo-2.3",
            "duration":   duration,
            "resolution": "1080P",
        }

        print(f"REPLICATE i2v: model={IMAGE_TO_VIDEO_MODEL} prompt={prompt!r} image={image_url[:80]}")
        output = replicate.run(IMAGE_TO_VIDEO_MODEL, input=inp)

        # replicate returns a FileOutput or URL string
        video_url = str(output) if output else None
        if not video_url:
            return None, f"REPLICATE i2v: empty output — model returned {output!r}"

        print(f"REPLICATE i2v: done — {video_url[:80]}")
        from app.services.social_service import _upload_to_cloudinary
        return _upload_to_cloudinary(video_url, resource_type="video"), None

    except replicate.exceptions.ReplicateError as e:
        return None, f"REPLICATE i2v ReplicateError: {e.status} — {e}"
    except Exception as e:
        return None, f"REPLICATE i2v {type(e).__name__}: {e}"


def text_to_video(prompt: str, duration: int = 5) -> tuple[str | None, str | None]:
    """
    Generate a video from a text prompt only.
    Returns (video_url, error_message).
    """
    err = _check_token()
    if err:
        return None, err
    if not prompt:
        return None, "text_to_video: prompt is required"

    try:
        print(f"REPLICATE t2v: model={TEXT_TO_VIDEO_MODEL} prompt={prompt!r}")
        output = replicate.run(TEXT_TO_VIDEO_MODEL, input={
            "prompt":     prompt,
            "model":      "MiniMax-Hailuo-2.3",
            "duration":   duration,
            "resolution": "1080P",
        })

        video_url = str(output) if output else None
        if not video_url:
            return None, f"REPLICATE t2v: empty output — model returned {output!r}"

        print(f"REPLICATE t2v: done — {video_url[:80]}")
        from app.services.social_service import _upload_to_cloudinary
        return _upload_to_cloudinary(video_url, resource_type="video"), None

    except replicate.exceptions.ReplicateError as e:
        return None, f"REPLICATE t2v ReplicateError: {e.status} — {e}"
    except Exception as e:
        return None, f"REPLICATE t2v {type(e).__name__}: {e}"
