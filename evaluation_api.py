# evaluation_api.py

import base64
import requests


def evaluate_prompt(api_url: str, image_id: str, prompt: str, timeout: int = 30):
    """
    Sends image_id + prompt to API2.
    Returns (score, image_bytes).
    Raises exception if failed.
    """

    payload = {
        "image_id": image_id,
        "prompt": prompt,
    }

    response = requests.post(api_url, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception("API2 returned success=False")

    score = data.get("score")
    image_b64 = data.get("image_b64")

    if score is None or image_b64 is None:
        raise Exception("Invalid API2 response")

    image_bytes = base64.b64decode(image_b64)

    return score, image_bytes