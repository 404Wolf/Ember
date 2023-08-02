import asyncio
from datetime import datetime
from time import time
from random import randint
from os import remove
from numpy import linspace
from math import ceil
import asyncssh as aiossh
import aiofiles
import json
import aiohttp
import utils
import logging

logger = logging.getLogger(__name__)


async def setupInstance(
    config: dict,
    instance: classmethod,
    accounts: list,
    target: str,
    offsets: tuple,
    vpsNum: int,
    droptime: int,
) -> None:
    """
    Create VPS and load up sniper onto it.

    Args:
        config (dict): same config dict as main script
        instance (str): vultr vps instance
        accounts (list(dicts)): iterrable with format [{"email":"<email>", "password":"<password>"}, ...]
        target (str): username to snipe
        offsets (list): itterable in the format (lowest-offset,highest-offset)
        vpsNum (int): vps number
        droptime (int): UNIX droptime of snipe
    """
    await asyncio.sleep(vpsNum*0.025)

    # sometimes instances glitch out
    if "id" not in instance.__dict__:
        return False

    # use aiofiles for file handling, since it's non-blocking
    async with aiofiles.open(f"temp/{instance.id}.json", mode="w") as setupFile:
        setupJson = {
            "target": target,
            "offsets": offsets,
            "vpsNum": int(vpsNum),
            "droptime": int(droptime),
            "accounts": accounts,
        }
        await setupFile.write(json.dumps(setupJson, indent=3))

    # wait for instance to finish being set up by vultr
    while True:
        ready = await instance.isReady()
        if ready:
            break
        await asyncio.sleep(vpsNum)

    while True:
        # Continue to try to connect to the VPS, until the connection succeeds
        try:
            logger.debug("Attempting connection on " + instance.ip + "...")
            async with aiossh.connect(
                instance.ip,
                username=instance.username,
                password=instance.password,
                known_hosts=None,
            ) as chan:
                # create sftp connection and send needed files
                async with chan.start_sftp_client() as sftp:
                    await sftp.put(f"config.json", "config.json")
                    await sftp.put(f"temp/{instance.id}.json", "setup.json")
                    await sftp.put("sniper.py", "sniper.py")
                    logger.debug("Placed files into " + instance.ip)

                # run terminal commands/run sniper
                for command in config["sniper"]["setupCommands"]:
                    await chan.run(command)
                    logger.debug('Ran command "' + command + '" on ' + instance.ip)

            break  # vps has successfully been set up

        except OSError:  # OSError = connection timed out (vps isn't ready yet)
            logger.debug(instance.ip + " is not ready yet. Waiting and trying again...")
            await asyncio.sleep(2)

    # log that vps has been set up
    await utils.send(
        f"```Set up snipe for {target} on vps #{vpsNum}\nVPS ip: {instance.ip}\nVPS id: {instance.id}```"
    )

    # remove temp file after sending it to the VPS
    remove(f"temp/{instance.id}.json")


async def awaitSnipe(
    config: dict,
    queue,
    target: str,
    offsets: list,
    droptime: int,
    sniperTag="Sniper" + str(randint(10000, 99999)),
) -> None:
    """
    Wait for near-before-snipe, then create vpses and set them up.

    Args:
        config (dict): same config dict as main script
        queue (utils.queue): queue object from main script 
        target (str): name to snipe
        offsets (list or tuple): itterable in the format (lowest-offset,highest-offset)
        droptime (int): UNIX time of name drop
        sniperTag (str): tag to give vultr vps
    """
    # load in accounts
    async with aiofiles.open("accounts.txt") as accounts:
        accounts = await accounts.read()
        accounts = accounts.split("\n")
        accountsCount = len(accounts)
        accounts = map(lambda account: account.split(":"), accounts)

    # print that task has started
    logger.info('Snipe readied up for "' + target + '"')

    # wait until config["general"]["vpsBootTime"] minutes before droptime to begin readying up
    try:
        while time() + (config["general"]["vpsBootTime"] * 60) < droptime:
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        # if the task is cancelled whilst waiting, print a message and end
        logger.info(f"Ending snipe task for {target}")
        raise asyncio.CancelledError

    # log the offsets being used for the snipe,
    # before the snipe goes down, so that there's a record
    discordJson = {
        "content": None,
        "embeds": [
            {
                "title": "Offset Logs",
                "description": f"Offset logs for **{target}**...",
                "color": 000000,
                "fields": [
                    {"name": "Target:", "value": target, "inline": True},
                    {
                        "name": "Offsets:",
                        "value": f"From **{offsets[0]}** to **{offsets[1]}**",
                        "inline": True,
                    },
                    {
                        "name": "Date:",
                        "value": str(
                            datetime.utcfromtimestamp(time()).strftime("%m-%d-%Y")
                        ),
                        "inline": True,
                    },
                ],
                "thumbnail": {"url": config["general"]["emberThumbnail"]},
            }
        ],
    }

    async with aiofiles.open("logs/offsets.json") as offsetsLogsFile:
        offsetsLogs = json.loads(await offsetsLogsFile.read())
        offsetsLogs[target] = {"time": time(), "offsets": offsets, "droptime": droptime}
    async with aiofiles.open("logs/offsets.json", "w") as offsetsLogsFile:
        await offsetsLogsFile.write(json.dumps(offsetsLogs, indent=3))

    async with aiohttp.ClientSession() as session:
        await session.post(url=config["general"]["queueLogWebhook"], json=discordJson)

    # split up the offsets into equal parts
    # linspace -> (startingValue, endingValue, numberOfValues)
    offsets = tuple(
        linspace(
            offsets[0],
            offsets[1],
            ceil(accountsCount / config["general"]["accountsPer"]),
        )
    )

    # send status message
    await utils.send(
        f"Offsets have been calculated for target [{target}]"
        + f"(https://namemc.com/search?q={target}).\n\n```{tuple(map(lambda offset: round(offset, 2), offsets))}```"
    )
    logger.info('Offsets calculated for "' + target + '"')

    # create accounts array
    accounts = [
        {
            "email": email,
            "password": password,
        }
        for email, password in accounts
    ]

    # log that accounts were loaded in
    await utils.send(f'Loaded {accountsCount} accounts from the "accounts.txt"')

    async with aiohttp.ClientSession() as session:
        # create all the sniping VPSes
        instances = [
            utils.vultr.instance(
                config["sniper"]["vultr"]["bearer"],
                session,
                label="SnipeServer" + str(instance + 1),
                tag=sniperTag,
                region=config["sniper"]["vultr"]["region"],
                plan=config["sniper"]["vultr"]["plan"],
                snapshotId=config["sniper"]["vultr"]["snapshotId"],
            )
            for instance in range(
                ceil(len(accounts) / config["general"]["accountsPer"])
            )
        ]

        # prepare vps instances
        tasks = []
        for instance in instances:
            instance.username = "root"
            instance.password = config["sniper"]["vultr"]["snapshotPassword"]
            tasks.append(asyncio.create_task(instance.create()))
        await asyncio.wait(tasks)
        await utils.send("Created instances.")

        # print status message
        await utils.send("Waiting for servers to boot...")

        tasks = []  # call setup function for each server
        for counter, instance in enumerate(instances):
            # accountSelection is the current array of accounts to use
            try:
                accountSelection = accounts[
                    counter
                    * config["general"]["accountsPer"] : counter
                    * config["general"]["accountsPer"]
                    + config["general"]["accountsPer"]
                ]
            except IndexError:
                accountSelection = accounts[counter:]

            tasks.append(
                asyncio.create_task(
                    setupInstance(
                        config,
                        instance,
                        accountSelection,
                        target,
                        offsets,
                        counter + 1,
                        droptime,
                    )
                )
            )

        # wait for servers to finish booting
        await asyncio.wait(tasks)
        await utils.send("Servers all loaded, ready for sniping!")

        try:  # close servers after sniping finishes
            await asyncio.sleep(droptime - time())
            await utils.send("Snipes went down!")
            await asyncio.sleep(len(instances) * 4)

        finally:
            # remove all sniping instances
            for counter, instance in enumerate(instances, start=1):
                destruction = await instance.destroy()
                if destruction == 204:
                    await utils.send(f"Destroyed instance #{counter}")
                else:
                    await utils.send(
                        f"Failed to destroy instance #{counter} ({destruction})"
                    )
                await asyncio.sleep(0.1)
            await utils.send("Destroyed sniping instances")

            # remove the target from the queue
            await queue.remove(target)
            await utils.send("Removed target from queue")
