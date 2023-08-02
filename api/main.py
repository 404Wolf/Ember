# set up logging
import logging
import sys
import os
os.system('cls' if os.name=='nt' else 'clear')
print("""
 ___       _                 _   ___ ___ 
| __|_ __ | |__  ___ _ _    /_\ | _ \_ _|
| _|| '  \| '_ \/ -_) '_|  / _ \|  _/| | 
|___|_|_|_|_.__/\___|_|   /_/ \_\_| |___|
"""[1:])
logging.basicConfig(
    level=logging.DEBUG,
    filename="logs/logging.txt",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("discord").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

#import other modules
logging.info("Importing modules...")
import json
import asyncio
import utils
import workers
import setup
logging.debug("Modules imported.")

# asyncio background tasks
snipingTasks = {}
backgroundTasks = []

# load in configs
config = json.load(open("config.json"))
queue = utils.queue(config)

async def main() -> None:
    """Enable api and setup background tasks"""

    firstRun = True  # this is the first runthrough
    while True:
        # ensure auto restart of namemc every hour
        await utils.namemc.setup(
            config["discord"]["token"],
            config["discord"]["server"],
            config["discord"]["channels"]["namemc"],
        )

        if firstRun:
            # begin background tasks upon first run
            backgroundTasks = [
                setup.startApi(config, queue),
                queue.setup(),
                setup.targetScan(queue),
                workers.misc.discordWebhookCooldown(),
            ]
            [asyncio.create_task(task) for task in backgroundTasks]

            firstRun = False

        await asyncio.sleep(60*60)  # wait an hour between NameMC task restarts
        logging.debug("Restarting NameMC task...")
        

# set the event policy to windows if the user is using windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    # begin
    asyncio.run(main())
