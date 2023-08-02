from aiohttp_apispec import docs
import random
import secrets
import json
import asyncio
from aiohttp import web
import utils
from aiohttp_apispec import docs, headers_schema
import datetime
from time import time
from workers import schemas


# for /accountGen endpoint
names = json.load(open("utils/files/names.json"))
words = json.load(open("utils/files/words.json"))

# pending discord message sends
discordSendQueue = []


async def discordWebhookCooldown():
    """Ensure continuous resolution of the discordSendQueue + pauses"""
    while True:
        if len(discordSendQueue) > 0:
            for index, data in enumerate(discordSendQueue):
                message = data["message"]
                del data["message"]
                await utils.send(message, **data)
                del discordSendQueue[index]
                await asyncio.sleep(1.75)
        else:
            await asyncio.sleep(0.5)


@docs(
    tags=["misc"],
    summary="generate random human-looking account details",
    description="generate <count> number of account details",
    responses={
        200: {"description": "accounts generated successfully"},
    },
)
@headers_schema(schemas.accountGen)
async def accountGen(request: web.Request, **kwargs) -> web.Response:
    try:
        count = request.headers["count"]
    except KeyError:
        count = 1

    accounts = []

    for i in range(count):
        date = datetime.datetime.utcfromtimestamp(
            random.randint(788936400, round(time() - 567600500))
        )

        name = (
            random.choice(names["first"]).title()
            + " "
            + random.choice(names["last"]).title()
        )

        accounts.append(
            {
                "name": name,
                "email": f"{name.replace(' ', '')}{str(random.randint(100000, 999999))}@outlook.com",
                "gamertag": random.choice(words).title() + random.choice(words).title(),
                "DOB": f"{date.strftime('%B ')} {date.strftime('%d, ').replace('0', '')} {date.strftime('%Y')}",
                "password": secrets.token_urlsafe(24),
            }
        )

    return web.json_response(accounts)


@docs(
    tags=["misc"],
    summary="obtain the config json",
    description="returns the config json",
    responses={
        200: {"description": "successfully returned config json"},
    },
)
@headers_schema(schemas.accountGen)
async def config(request: web.Request, config=None, **kwargs) -> web.Response:
    return web.json_response(config)


@docs(
    tags=["misc"],
    summary="forward a discord webhook/message/embed",
    description="forward either a string (as a status update message) or dict (as an embed) to a given discord webhook",
    responses={
        200: {"description": "successfully sent message"},
    },
)
@headers_schema(schemas.sendToDiscord)
async def discord(request: web.Request, **kwargs) -> web.Response:
    kwargs = {}

    if "webhook" in request.headers:
        kwargs["webhook"] = request.headers["webhook"]
    if "vps" in request.headers:
        kwargs["vps"] = request.headers["vps"]

    discordSendQueue.append({"message": request.headers["message"], **kwargs})
    return web.Response(status=204)

async def home(request: web.Request, **kwargs):
    raise web.HTTPFound('/api/docs')
