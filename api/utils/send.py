from json.decoder import JSONDecodeError
import logging
import datetime
import aiohttp
from time import time
import json

logger = logging.getLogger(__name__)
config = json.load(open("config.json"))


async def send(
    discordJson, webhook=config["general"]["botStatusWebhook"], vps="Main"
) -> None:
    """
    Send parsed log embed to botStatusWebhook discord chat.

    Args:
        message: message to send
        delay: delay to wait before sending in secs
        printing: print to console too
    """
    logger.info(f'Forwarding message: "{discordJson}" to discord...')

    try:
        discordJson = json.loads(discordJson)
    except JSONDecodeError:
        pass

    if isinstance(discordJson, str):
        discordJson = {
            "content": None,
            "embeds": [
                {
                    "title": "Status Update",
                    "description": discordJson,
                    "color": str(15157547),
                    "fields": [
                        {
                            "name": "Time:",
                            "value": str(
                                datetime.datetime.utcfromtimestamp(time()).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                            ),
                            "inline": True,
                        },
                        {"name": "VPS:", "value": vps, "inline": True},
                    ],
                    "thumbnail": {"url": config["general"]["emberThumbnail"]},
                }
            ],
        }
    elif not isinstance(discordJson, dict):
        errorMsg = "Message/embed to forward to discord must be a properly formatted json or a string-message"
        logger.critical(errorMsg)
        raise TypeError(errorMsg)

    async with aiohttp.ClientSession() as session:
        await session.post(webhook, json=discordJson)  # send the embed to the chat
