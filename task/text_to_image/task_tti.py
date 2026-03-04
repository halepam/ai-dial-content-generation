import asyncio
from datetime import datetime
import io
from typing import Optional

import requests

from task._models.custom_content import Attachment
from task._utils.constants import API_KEY, DIAL_URL, DIAL_CHAT_COMPLETIONS_ENDPOINT
from task._utils.bucket_client import DialBucketClient
from task._utils.model_client import DialModelClient
from task._models.message import Message
from task._models.role import Role
from task.constants import DIAL_ENDPOINT


class Size:
    """
    The size of the generated image.
    """

    square: str = "1024x1024"
    height_rectangle: str = "1024x1792"
    width_rectangle: str = "1792x1024"


class Style:
    """
    The style of the generated image. Must be one of vivid or natural.
     - Vivid causes the model to lean towards generating hyper-real and dramatic images.
     - Natural causes the model to produce more natural, less hyper-real looking images.
    """

    natural: str = "natural"
    vivid: str = "vivid"


class Quality:
    """
    The quality of the image that will be generated.
     - ‘hd’ creates images with finer details and greater consistency across the image.
    """

    standard: str = "standard"
    hd: str = "hd"


def _save_image_locally(
    filename: Optional[str], image_url: Optional[str], ext: str = ".png"
) -> None:
    """
    Save the image from the url locally to disk
    """
    try:
        if not filename or not image_url:
            print("Failed to save, no filename or image url is passed")
            return
        response = requests.get(image_url, headers={"Api-Key": API_KEY})
        if response.status_code != 200:
            return None
        filename_path = filename + ext
        with open(filename_path, "wb") as writer:
            writer.write(response.content)
            print(f"Successfully saved to local disk: {filename_path}")
    except Exception as e:
        print(f"Failed to save: {e}")


def _read_image_url_as_binary(image_url) -> Optional[io.BytesIO]:
    """
    Reads an image from a URL and returns its binary content (bytes object).
    """
    try:
        # Send a GET request to the URL
        response = requests.get(image_url, headers={"Api-Key": API_KEY})
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to retrieve image from URL: {image_url}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


async def _save_images(attachments: list[Attachment]) -> list[io.BytesIO]:
    # TODO:
    #  1. Create DIAL bucket client
    base64_attachments = []
    async with DialBucketClient(API_KEY, DIAL_ENDPOINT) as client:
        #  2. Iterate through Images from attachments, download them and then save here
        for attachment in attachments:
            print(f"Received attachment: {attachment}")
            if attachment.type is None:
                continue
            if not attachment.type.startswith("image"):
                continue
            base64_content = _read_image_url_as_binary(
                DIAL_ENDPOINT + "/v1/" + attachment.url
            )
            if base64_content:
                base64_attachments.append(base64_content)
            upload_result = await client.put_file(
                name=attachment.title,
                mime_type=attachment.type,
                content=base64_content,
            )
            _save_image_locally(
                upload_result.get("name"), DIAL_URL + "/v1/" + upload_result.get("url")
            )

    #  3. Print confirmation that image has been saved locally
    print("Successfully saved the images locally")
    return base64_attachments


async def start() -> None:
    # TODO:
    #  1. Create DialModelClient
    client = DialModelClient(DIAL_CHAT_COMPLETIONS_ENDPOINT, "dall-e-3", API_KEY)
    #  2. Generate image for "Sunny day on Bali"
    message = client.get_completion(
        messages=[
            Message(role=Role.USER, content='Generate image for "Sunny day on Bali"')
        ],
        custom_fields={
            "size": Size.square,
            "style": Style.natural,
            "quality": Quality.standard,
        },
    )
    #  3. Get attachments from response and save generated message (use method `_save_images`)
    await _save_images(message.custom_content.attachments)
    #  4. Try to configure the picture for output via `custom_fields` parameter.
    #    - Documentation: See `custom_fields`. https://dialx.ai/dial_api#operation/sendChatCompletionRequest
    #  5. Test it with the 'imagegeneration@005' (Google image generation model)


asyncio.run(start())
