# challenge_api.py

import base64
import requests


def fetch_challenge_image(api_url: str, timeout: int = 15):
    """
    Calls API1 and returns (image_bytes, image_id).
    Raises Exception if API fails.
    """

    response = requests.post(api_url, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception("API returned success=False")

    image_b64 = data.get("image_b64")
    image_id = data.get("image_id")

    if not image_b64:
        raise Exception("No image_b64 in response")

    # Decode base64 → bytes
    image_bytes = base64.b64decode(image_b64)

    return image_bytes, image_id