# set up logging
import logging
import sys
import os
os.system('cls' if os.name=='nt' else 'clear')
print("""
 ___       _               ___  _                   _ 
| __|_ __ | |__  ___ _ _  |   \(_)___ __ ___ _ _ __| |
| _|| '  \| '_ \/ -_) '_| | |) | (_-</ _/ _ \ '_/ _` |
|___|_|_|_|_.__/\___|_|   |___/|_/__/\__\___/_| \__,_|
 """[1:])
logging.basicConfig(
    level=logging.DEBUG,
    filename="logging.txt",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger("discord").setLevel(logging.CRITICAL)

#import other modules
import discord
from discord.commands import SlashCommandGroup
from discord.commands import Option
import datetime
import logging
import asyncio
import requests
import aiohttp
import json
from math import inf
import utils
import aiofiles

config = json.load(open("config.json"))
apiLogin = (
    config["api"]["login"]["username"],
    config["api"]["login"]["password"],
)
aiohttpApiLogin = aiohttp.helpers.BasicAuth(*apiLogin)
apiUrl = "http://" + config["api"]["ip"] + ":" + str(config["api"]["port"])
config = requests.get(apiUrl + "/config", auth=apiLogin).json()
client = discord.Bot()
logging.debug("Modules imported.")

# create slash command groups
queueCommands = SlashCommandGroup(
    "queue",
    "Commands for updating the current queue.",
    guild_ids=[config["discord"]["server"]],
)

logCommands = SlashCommandGroup(
    "logs",
    "Commands for retreive logs.",
    guild_ids=[config["discord"]["server"]],
)


@client.event
async def on_ready():
    """Bot has readied up"""
    global session

    backgroundTasks = []
    try:
        logging.info("Bot has booted")
        session = aiohttp.ClientSession()

        backgroundTasks.append(
            asyncio.create_task(
                utils.tasks.queueEmbed(client, apiUrl, session, aiohttpApiLogin, config)
            )
        )

        await asyncio.sleep(inf)
    finally:
        for task in backgroundTasks:
            task.cancel()

        await session.close()


async def getQueue(ctx: discord.AutocompleteContext):
    """Fetch items in the queue for autocompleting slash commands"""
    return await utils.helpers.getQueue(session, apiUrl, aiohttpApiLogin)


async def getPastSnipes(ctx: discord.AutocompleteContext):
    """Fetch every snipe"""
    return await utils.helpers.getPastSnipes(session, apiUrl, aiohttpApiLogin)


async def ensureBotChat(message: discord.Message):
    if message.channel.id != config["discord"]["channels"]["botChat"]:
        responseEmbed = discord.Embed(
            title=f"Unable to preform command",
            description=f"This command can only be used in <#{config['discord']['channels']['botChat']}>",
            colour=config["general"]["colour"],
        )
        responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
        await message.respond(embed=responseEmbed, ephemeral=True)
        return False
    return True


@queueCommands.command(name="add", description="Add a target to the queue")
async def addToQueue(
    message: discord.Message,
    target: Option(str, "target to add to queue", required=True),
    min_offset: Option(
        float, "min offset for item being added to queue", required=True, default=0
    ),
    max_offset: Option(
        float, "max offset for item being added to queue", required=True
    ),
    droptime: Option(
        int,
        "UNIX droptime for target (scrapes from NameMC if not included)",
        required=False,
    ),
):
    """Add a given target to the queue"""
    body = {"target": target, "offsets": [min_offset, max_offset]}  # POST request body
    if (
        droptime != None
    ):  # droptime is optional, but if they include it then ensure it is used
        body["droptime"] = droptime
    async with session.post(apiUrl + "/queue", json=body, auth=aiohttpApiLogin) as resp:
        if resp.status == 200:  # success
            logging.info(
                f'Added "{target}" to queue with offsets between {min_offset}ms and {max_offset}ms'
            )
            responseEmbed = discord.Embed(
                title=f'"{target}" added to queue successfully',
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
            )
            responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
            responseEmbed.add_field(name="Target", value=target)
            responseEmbed.add_field(
                name="Offsets", value=f"Between {min_offset} and {max_offset}"
            )
            await message.respond(embed=responseEmbed, ephemeral=True)
            return
        else:
            logging.critical(
                f'Failed to add "{target}" to queue (status code {resp.status})'
            )
            if resp.status == 400:  # not dropping
                errorMsg = (
                    f'Error: "{target}" is not dropping or it is too close to the drop'
                )
            elif resp.status == 208:  # already in queue
                errorMsg = f'Error: "{target}" is already in queue'
            else:
                errorMsg = f"Error: unknown error (received status code {resp.status})"
            logging.critical(errorMsg)
            responseEmbed = discord.Embed(
                title=f'Failed to add "{target}" to queue',
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
                description=errorMsg,
            )
            responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
            responseEmbed.add_field(name="Target", value=target)
            responseEmbed.add_field(
                name="Offsets", value=f"Between {min_offset} and {max_offset}"
            )
        await message.respond(embed=responseEmbed, ephemeral=True)


@queueCommands.command(
    name="mass-add", description="Add many comma seperated targets to queue"
)
async def addToQueue(
    message: discord.Message,
    targets: Option(str, "comma seperated targets to add to queue", required=True),
    min_offset: Option(
        float, "min offset for item being added to queue", required=True, default=0
    ),
    max_offset: Option(
        float, "max offset for item being added to queue", required=True
    ),
):
    """Add many targets to the queue"""

    if not await ensureBotChat(message):
        return

    targets = targets.split(",")  # split targets every ","
    targets = tuple(
        map(lambda target: target.strip(), targets)
    )  # trim off whitespace from targest
    targets = tuple(set(targets))  # remove duplicates
    responseEmbed = discord.Embed(
        title="Loading...",
        description="See embed below for live updates ⬇️",
        colour=config["general"]["colour"],
    )
    responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
    await message.respond(embed=responseEmbed)

    response = await message.channel.send(
        "** **"
    )  # send blank message to be used for updates on queue addition

    successes = []  # targets successfully added to queue
    failures = []  # targets which couldn't be added to queue

    try:
        for target in targets:
            responseEmbed = discord.Embed(
                title=f'Adding "{target}" to queue...',
                colour=config["general"]["colour"],
            )

            responseEmbed.add_field(
                name="Offsets",
                value=f"Between {min_offset} and {max_offset}",
                inline=False,
            )

            if len(successes) > 0:
                responseEmbed.add_field(
                    name=f"Successes ({len(successes)})",
                    value=f"```" + "\n".join(successes) + "```",
                    inline=False,
                )

            if len(failures) > 0:
                responseEmbed.add_field(
                    name=f"Failures ({len(failures)})",
                    value=f"```" + "\n".join(failures) + "```",
                    inline=False,
                )

            response = await response.edit(embed=responseEmbed)

            body = {
                "target": target,
                "offsets": [min_offset, max_offset],
            }  # POST request body

            async with session.post(
                apiUrl + "/queue", json=body, auth=aiohttpApiLogin
            ) as resp:
                if resp.status == 200:  # success
                    successes.append(f'"{target}"')
                else:
                    failures.append(f'"{target}" [{resp.status}]')

    finally:
        logging.warning(failures)
        if len(targets) == len(successes):
            responseEmbed.title = "All targets successfully added to queue"
        elif len(successes) == 0:
            responseEmbed.title = "Failed to add any targets to queue"
        else:
            responseEmbed.title = "Some targets added to queue"
        response = await response.edit(embed=responseEmbed)


@queueCommands.command(
    name="update", description="Update the offsets of a target already in the queue"
)
async def updateQueue(
    message: discord.Message,
    target: Option(
        str,
        "target to have its offsets updated",
        autocomplete=getQueue,
        required=True,
    ),
    min_offset: Option(
        float, "min offset for item being updated in queue", required=True, default=0
    ),
    max_offset: Option(
        float, "max offset for item being updated in queue", required=True
    ),
):
    """Update the delays for a name in the queue"""
    responses = []

    class BadResponseCode(Exception):
        pass

    try:
        # make request to fetch the current queue
        async with session.get(apiUrl + "/queue", auth=aiohttpApiLogin) as resp:
            responses.append({"get queue req": resp.status})
            if resp.status == 200:
                logging.debug(f"Get queue request status code: {resp.status}")
                data = await resp.json()
                droptime = data[target]["droptime"]
            else:
                raise BadResponseCode(resp.status)

            # make request to remove target from queue
            async with session.delete(
                apiUrl + "/queue", headers={"target": target}, auth=aiohttpApiLogin
            ) as resp:
                logging.debug(f"Remove target from queue status code: {resp.status}")
                responses.append({"remove from queue req": resp.status})
                if resp.status == 200:
                    body = {
                        "target": target,
                        "offsets": [min_offset, max_offset],
                        "droptime": droptime,
                    }
                else:
                    raise BadResponseCode(resp.status)

                # make request to add target back to queue
                async with session.post(
                    apiUrl + "/queue", json=body, auth=aiohttpApiLogin
                ) as resp:
                    logging.debug(f"Add name back to queue status code: {resp.status}")
                    if resp.status == 200:
                        responses.append({"add back to queue req"})
                        responseEmbed = discord.Embed(
                            title=f'"{target}" updated successfully',
                            url=f"https://namemc.com/search?q={target}",
                            colour=config["general"]["colour"],
                        )
                        responseEmbed.set_thumbnail(
                            url=config["general"]["emberThumbnail"]
                        )
                        responseEmbed.add_field(name="Target", value=target)
                        responseEmbed.add_field(
                            name="Offsets",
                            value=f"Between {min_offset}ms and {max_offset}ms",
                        )
                        await message.respond(embed=responseEmbed, ephemeral=True)
                        return
                    else:
                        raise BadResponseCode(resp.status)

    except KeyError:
        errorMsg = f'Error: "{target}" was not in queue to begin with'
    except BadResponseCode:
        errorMsg = f"Error: failed request (received status codes `{responses}`)"
    except:
        errorMsg = "Error: unknown error"

    logging.critical(errorMsg)
    responseEmbed = discord.Embed(
        title=f'Failed to update "{target}"',
        url=f"https://namemc.com/search?q={target}",
        colour=config["general"]["colour"],
        description=errorMsg,
    )
    responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
    responseEmbed.add_field(name="Target", value=target)
    responseEmbed.add_field(
        name="Offsets", value=f"Between {min_offset} and {max_offset}"
    )
    await message.respond(embed=responseEmbed, ephemeral=True)


@queueCommands.command(name="remove", description="Remove a target from the queue")
async def removeFromQueue(
    message: discord.Message,
    target: Option(
        str,
        "target to remove from queue",
        autocomplete=getQueue,
        required=True,
    ),
):
    """Remove a given target from the queue"""
    async with session.delete(
        apiUrl + "/queue", headers={"target": target}, auth=aiohttpApiLogin
    ) as resp:
        if resp.status == 200:  # success
            logging.info(f'Removed "{target}" from queue')
            responseEmbed = discord.Embed(
                title=f'"{target}" removed from queue successfully',
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
            )
        else:
            if resp.status == 404:
                errorMsg = f'Error: "{target}" was not in the queue to begin with'
            else:
                errorMsg = f"Error: unknown error (received status code {resp.status})"
            logging.critical(errorMsg)
            responseEmbed = discord.Embed(
                title=f'Failed to remove "{target}" from queue',
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
                description=errorMsg,
            )
        responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
        await message.respond(embed=responseEmbed, ephemeral=True)


@logCommands.command(name="times", description="Get the send/receive times of a target")
async def getLogTimes(
    message: discord.Message,
    target: Option(
        str,
        "target to retreive times for",
        autocomplete=getPastSnipes,
        required=True,
    ),
):
    if not await ensureBotChat(message):
        return

    async with session.get(
        apiUrl + "/logging/times/" + target, auth=aiohttpApiLogin
    ) as resp:
        data = await resp.json()
        if resp.status == 200:
            responseEmbed = discord.Embed(
                title=f"Time logs for {target}",
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
            )

            times = f'Time logs for "{target}"\n\n'

            times += "-----------------------------\n"
            times += "Send   | Receive      | Offset\n"
            times += "-----------------------------\n"
            for send, receive in zip(data["sends"], data["receives"]):
                times += f".{str(send['time']).split('.')[1][:5]} | .{str(receive['time']).split('.')[1][:5]} [{receive['code']}] | {'{:.5f}'.format(send['offset'])}\n"
            times += "-----------------------------"

            times += "\n\nDisclaimer:\n"
            times += "  Receive and sends are not lined up.\n"
            times += "  Both are ordered ascendingly by time.\n"
            times += "  Offsets are are lined up with sends."

            path = f"{target}-times.txt"

            async with aiofiles.open(path, "w") as timesFile:
                await timesFile.write(times)

            responseEmbed = discord.Embed(
                title=f'Successfully retreived time logs for "{target}"',
                description=f'⬆️ Time logs for the target "{target}" are included as a txt file above',
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
            )

            responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
            await message.respond(embed=responseEmbed, file=discord.File(path))
            # await message.channel.send(content="** **", file=discord.File(path))
            os.remove(path)

        else:
            if resp.status == 404:
                errorMsg = f"Error: time logs for target not found"
            else:
                errorMsg = f"Error: unknown error (received status code {resp.status})"
            logging.critical(errorMsg)
            responseEmbed = discord.Embed(
                title=f'Failed to retreive time logs for "{target}"',
                description=errorMsg,
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
            )

            responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
            await message.respond(embed=responseEmbed)


@logCommands.command(
    name="offsets", description="Get the offsets that were used for a target's snipe"
)
async def getLogTimes(
    message: discord.Message,
    target: Option(
        str,
        "target to retreive offsets for",
        autocomplete=getPastSnipes,
        required=True,
    ),
):
    if not await ensureBotChat(message):
        return

    async with session.get(
        apiUrl + "/logging/offsets/" + target, auth=aiohttpApiLogin
    ) as resp:
        data = await resp.json()
        if resp.status == 200:
            responseEmbed = discord.Embed(
                title=f'Offset logs for "{target}"',
                description=f'Below are the offsets and droptime of the past snipe for the target "{target}"',
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
            )
            responseEmbed.add_field(
                name="Offsets used", value=data["offsets"], inline=False
            )

            timeString = datetime.datetime.fromtimestamp(data["droptime"])
            responseEmbed.add_field(
                name="Droptime (UTC)", value=timeString, inline=False
            )
            responseEmbed.add_field(
                name="Droptime (UNIX)", value=data["droptime"], inline=False
            )

        else:
            if resp.status == 404:
                errorMsg = f"Error: offset logs for target not found"
            else:
                errorMsg = f"Error: unknown error (received status code {resp.status})"
            logging.critical(errorMsg)
            responseEmbed = discord.Embed(
                title=f'Failed to offset logs for "{target}"',
                description=errorMsg,
                url=f"https://namemc.com/search?q={target}",
                colour=config["general"]["colour"],
            )
    responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
    await message.respond(embed=responseEmbed)


@client.slash_command(
    name="purge",
    description="Purge all messages from the chat",
    guild_ids=[config["discord"]["server"]],
)
async def purgeAll(message: discord.Message):
    """Purge the chat that this command was sent in"""
    await utils.helpers.purge(client, message.channel.id)
    await message.respond("The chat has been purged", ephemeral=True)


@client.slash_command(
    name="namemc",
    description="Gather namemc search data of a username",
    guild_ids=[config["discord"]["server"]],
)
async def namemc(
    message: discord.Message,
    target: Option(str, description="Target to fetch namemc data for", required=True),
):
    """Fetch namemc data for a username"""

    if not await ensureBotChat(message):
        return

    async with session.get(apiUrl + "/namemc/" + target, auth=aiohttpApiLogin) as resp:
        data = await resp.json()
        responseEmbed = discord.Embed(
            title=f'NameMC data for "{target}"',
            url=f"https://namemc.com/search?q={target}",
            colour=config["general"]["colour"],
        )
        responseEmbed.set_thumbnail(url=config["general"]["emberThumbnail"])
        responseEmbed.add_field(name="Target", value=data["target"])
        responseEmbed.add_field(name="Searches", value=data["searches"])
        responseEmbed.add_field(name="Status", value=data["status"])
        if data["droptime"] != None:
            timeString = datetime.datetime.fromtimestamp(data["droptime"])
            responseEmbed.add_field(name="Droptime (UTC)", value=timeString)
            responseEmbed.add_field(name="Droptime (UNIX)", value=data["droptime"])
        await message.respond(embed=responseEmbed)


# hook group slash commands to the client
client.add_application_command(queueCommands)
client.add_application_command(logCommands)

# boot the bot
client.run(config["discord"]["token"])
