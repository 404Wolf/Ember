from re import L
import discord
from random import randint, choice
from time import mktime
import asyncio
import datetime
import logging
import secrets

logger = logging.getLogger(__name__)
client = discord.Client()


async def setup(token, server, channelIds):
    """
    Sets up discord bot
    """
    global channels  # channel to be used for scraping

    asyncio.create_task(client.start(token))
    while True:
        guild = client.get_guild(server)
        if guild is None:
            await asyncio.sleep(0.5)
        else:
            break

    # change the bot's status to "Scraping NameMC"
    game = discord.Game("Ember Sniper Bot")
    await client.change_presence(status=discord.Status.online, activity=game)

    # fetch the channels
    channels = [await client.fetch_channel(channelId) for channelId in channelIds]

    # log that the api has booted
    logger.info("NameMC API has booted.")


async def lookup(target):
    """
    Get information about a name's status, droptime, and search count
    """
    global channels

    channel = choice(channels)

    data = {
        "target": target
    }  # create data dict. this function will return the data variable when complete

    while True:
        messageFromHist = False
        while (not messageFromHist) or (len(messageFromHist.embeds) == 0):
            # trigger embed generation
            link = f"https://namemc.com/search?q={target}&r={secrets.token_urlsafe(16)}"
            await channel.send(link)
            logger.debug('Sent namemc link to "' + channel.name + '"')

            # give time for embed to generate
            await asyncio.sleep(0.8)

            # get the most recent message in channel's history
            async for message in channel.history(
                limit=1
            ):  # fetch last message in channel message was sent to
                messageFromHist = message  # grab the message

            try:
                # raw is the embed's description string, which hopefully contains searches and other useful info
                raw = messageFromHist.embeds[0].description
            except IndexError:
                continue  # no embed found

            # ensure that it is the correct embed
            if target not in raw:
                logger.debug('"' + target + '" was not in the embed. Trying again...')
                continue

        try:
            # grab searches by parsing the embed's description string
            data["searches"] = int(
                raw[raw.find("Searches: ") :]
                .replace("Searches: ", "")
                .replace(" / month", "")
            )
        except:
            continue

        # check the status of the name:
        if (
            "Availability" in raw
        ):  # name is dropping if "Availability" is found in the embed
            # parse the droptime out of the raw embed string
            droptime = mktime(
                datetime.datetime.strptime(
                    raw[: raw.find("Z,")].replace("Time of Availability: ", ""),
                    "%Y-%m-%dT%H:%M:%S",
                ).timetuple()
            )
            data["status"] = "dropping"
            data[
                "droptime"
            ] = droptime  # since the name is dropping, there is a droptime, so set the output's "droptime" to the droptime
        elif "Unavailable" in raw:  # name is taken if "Unavailable" is in the embed
            data["status"] = "unavailable"
            data["droptime"] = None
        elif "Available*" in raw:  # name is not taken if "available" is in the embed
            data["status"] = "available"
            data["droptime"] = None
        elif (
            "Invalid" or "Too" in raw
        ):  # name is invalid and not taken if "Invalid" or "Too" is in the embed
            data["status"] = "invalid"
        else:
            continue

        logger.info("Successfully scraped data for " + target)

        return data  # finally, return the organized data output
