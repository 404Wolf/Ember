import asyncio
import utils


async def targetScan(queue: utils.queue) -> None:
    """
    Automatically remove targets which are no longer dropping from the queue

    Args:
        queue (utils.queue): the current queue object
    """

    await asyncio.sleep(15*60)

    while True:
        for target in queue.targets():
            validated = await queue.validate(target, tooCloseCheck=False)
            if not validated:
                await utils.send(validated["msg"])
                await queue.remove(target)
            await asyncio.sleep(60)  # cooldown