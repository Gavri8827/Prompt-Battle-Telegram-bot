# evaluation_api.py

import base64
import requests
import bot_secrets
import challenge_api
def evaluate_prompt(api_url: str, image_id: str, prompt: str, timeout: int = 30):
    """
    Sends image_id + prompt to API2.
    Returns (score, image_bytes).
    Raises exception if failed.
    """

    payload = {
        "user_prompt": prompt,
        "target_image_id": image_id,
    }

    response = requests.post(api_url, payload)
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


# image_bytes, image_id2 = challenge_api.fetch_challenge_image(bot_secrets.API1_URL)
# print(image_id2)
# score, image_byte = evaluate_prompt(bot_secrets.API2_URL, image_id2, "dog with suit")
#
# print(score)
# print("\n")
# print(image_byte)



