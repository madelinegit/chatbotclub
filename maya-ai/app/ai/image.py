import time
import requests
from app.config import MODELSLAB_API_KEY, MODELSLAB_IMAGE_URL, MODELSLAB_IMAGE_MODEL


def _poll_for_image(url: str, max_wait: int = 45) -> str | None:
    """Poll a future_links URL every 5 seconds until the image is ready."""
    for _ in range(max_wait // 5):
        time.sleep(5)
        try:
            r = requests.head(url, timeout=10)
            if r.status_code == 200:
                return url
        except Exception:
            pass
    return None


def generate_image(prompt: str) -> str | None:
    """Call ModelsLab text2img and return the image URL or None on failure."""
    payload = {
        "key":                  MODELSLAB_API_KEY,
        "model_id":             MODELSLAB_IMAGE_MODEL,
        "prompt":               prompt,
        "negative_prompt":      "bad quality, blurry, distorted, watermark",
        "width":                "512",
        "height":               "512",
        "samples":              "1",
        "num_inference_steps":  "30",
        "guidance_scale":       7.5,
        "safety_checker":       "no",
    }

    try:
        r = requests.post(MODELSLAB_IMAGE_URL, json=payload,
                          headers={"Content-Type": "application/json"}, timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"IMAGE API ERROR: {e}")
        return None

    if data.get("status") == "success":
        return data["output"][0]

    if data.get("status") == "processing":
        future_url = data.get("future_links", [None])[0]
        if future_url:
            return _poll_for_image(future_url)

    return None
