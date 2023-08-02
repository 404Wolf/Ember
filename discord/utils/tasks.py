import aiohttp
import asyncio
import discord
import utils
from time import time

async def queueEmbed(
    client: discord.Bot, apiUrl: str, session: aiohttp.ClientSession, aiohttpApiLogin: aiohttp.helpers.BasicAuth, config: dict
) -> None:
    """
    Auto update the queue, live
    
    Args:
        client (discord.Bot): discord client object
        apiUrl (str): url to the main api
        session (aiohttp.ClientSession): aiohttp client session object
        aiohttpApiLogin (aiohttp.helpers.BasicAuth): aiohttp HTTP basic autherisation object
        config (dict): main config dict
    """

    async def createQueueEmbed(colour: int) -> discord.Embed:
        """
        Generate an discord.Embed of the current queue.

        Args:
            colour (int): colour code for embed side colour
        """

        try:
            resp = await session.get(
                apiUrl + "/queue", auth=aiohttpApiLogin, timeout=aiohttp.ClientTimeout(total=6)
            )
        except asyncio.TimeoutError:
            return discord.Embed(
                colour=colour,
                title=f"Failed to load queue",
                description=description,
            )

        if resp.status == 204:
            description = "Use `/queue add <target> <offsets>` to add a target to the queue.\n\n"
            description += "Names added to the queue will show up here."
            return discord.Embed(
                colour=colour,
                title=f"No items in queue",
                description=description,
            )

        description = (
            "Targets queued to be sniped are listed in ascending order (by time until drop) below."
        )
        newQueueEmbed = discord.Embed(
            colour=colour, title=f"Current Queue", description=description
        )
        newQueueEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])

        queue = await resp.json()  # queue as dict

        queueItems = queue.items()  # convert dict to 2d array
        queueItems = sorted(
            tuple(queueItems),
            key=lambda queueItem: queueItem[1]["droptime"],
            reverse=False,
        )  # sort by droptimes (closest to drop first)

        # include disclaimer about how queue is overfull?
        if len(queueItems) > config["general"]["visibleQueueCap"]:
            omitted = len(queueItems) - config["general"]["visibleQueueCap"]
            extras = True
        else:
            extras = False

        queueItems = tuple(queueItems)[:config["general"]["visibleQueueCap"]]

        targets = []
        offsets = []
        hoursUntil = []

        counter = 0
        for target, data in queueItems:
            startOffsets = data["offsets"][0]
            endOffset = data["offsets"][1]
            droptime = data["droptime"]
            minutesUntilDrop = (droptime - time()) / 60

            if counter <= 5:
                targets.append(f"[{target}](http://mine.ly/{target})")
            else:
                targets.append(target)

            offsets.append(f"{startOffsets}-{endOffset}ms")
            hoursUntil.append(f"{round(minutesUntilDrop/60,2)}hrs")
            counter += 1

        newQueueEmbed.add_field(name="Targets", value="\n".join(targets))
        newQueueEmbed.add_field(name="Offsets", value="\n".join(offsets))
        newQueueEmbed.add_field(
            name="Hrs Until Drop", value="\n".join(hoursUntil)
        )

        if extras:  # if items were omitted, note it in the embed description
            newQueueEmbed.description += f"\n\nNote: there are over {config['general']['visibleQueueCap']} "
            newQueueEmbed.description += f"targets in the queue ({len(targets)+omitted}), so {omitted} targets were omitted."
        return newQueueEmbed  # return output string

    await utils.helpers.purge(client, config["discord"]["channels"]["queue"])
    queueChannel = client.get_channel(config["discord"]["channels"]["queue"])

    queueEmbed = await queueChannel.send(
        content="** **"
    )  # send empty message (will be used for queue embed)
    await queueEmbed.pin()  # pin queue embed to chat

    # begin generation of a live embed
    try:
        while True:
            for colour in (
                config["general"]["colour"] + 5,
                config["general"]["colour"] - 150,
            ):
                try:
                    newQueueEmbed = await createQueueEmbed(colour)
                    await queueEmbed.edit(embed=newQueueEmbed)
                except:
                    pass
                finally:
                    await asyncio.sleep(2.25)
    finally:
        await queueEmbed.edit(
            embed=discord.Embed(
                colour=config["general"]["colour"],
                title=f"Bot is offline",
                description="Please boot the bot to view the queue.",
            )
        )
        await session.close()
