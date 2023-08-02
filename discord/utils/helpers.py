from typing import Optional
import discord
import aiohttp


async def purge(client: discord.Bot, channelId: int, lapses=1) -> None:
    """
    Purges all messages <14 days old from a channel.

    Args:
        client (discord.Bot): discord bot object
        channelId (int): id of channel to purge
        lapses (int): how many passes of 100 deletions to run
    """
    for i in range(lapses):
        messages = []  # list of message to be deleted
        async for message in client.get_channel(channelId).history(limit=100):
            messages.append(message)
        await client.get_channel(channelId).delete_messages(messages)


async def getQueue(
    session: aiohttp.ClientSession,
    apiUrl: str,
    aiohttpApiLogin: aiohttp.helpers.BasicAuth,
) -> tuple:
    """
    Get a tuple of the current queue's names in order of droptime.

    Args:
        session (aiohttp.ClientSession): aiohttp session
        config (dict): config from the config.json
        apiUrl (str): url to the api
        aiohttpApiLogin (aiohttp.helpers.BasicAuth): aiohttp HTTP basic autherisation object

    Returns:
        tuple: current queue, in order of when the names got queued
    """
    async with session.get(apiUrl + "/queue", auth=aiohttpApiLogin) as resp:
        data = await resp.json()
        output = data.items()
        output = sorted(output, key=lambda item: item[1]["droptime"])
        output = map(lambda item: item[0], output)
        return tuple(output)


async def getPastSnipes(
    session: aiohttp.ClientSession,
    apiUrl: str,
    aiohttpApiLogin: aiohttp.helpers.BasicAuth,
) -> tuple:
    """
    Get a tuple of the current queue's names in order of droptime.

    Args:
        session (aiohttp.ClientSession): aiohttp session
        config (dict): config from the config.json
        apiUrl (str): url to the api
        aiohttpApiLogin (aiohttp.helpers.BasicAuth): aiohttp HTTP basic autherisation object

    Returns:
        tuple: all past snipes in order of when they were sniped (most recent first)
    """
    async with session.get(apiUrl + "/logging/snipes", auth=aiohttpApiLogin) as resp:
        data = await resp.json()
        return tuple(data)
