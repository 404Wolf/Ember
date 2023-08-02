import json
import asyncio
import typing
import utils
from time import time
import logging
import string

logger = logging.getLogger(__name__)


class queue:
    """
    Container for the snipe queue.

    Attributes:
        config (dict): config file (from main api script)
        queueFile (str): filename of the queue json file
        queue (dict): the current queue
        pendingSnipes (list): list of asyncio tasks for pending snipes
    """

    def __init__(self, config: dict, queueFile="queue.json") -> None:
        """
        Initilize queue class.

        Args:
            config (dict): config file from main api script
            queueFile (str): name of queue file
        """
        self.config = config  # set the name of the config file as an attribute
        self.queueFile = queueFile  # set the name of the queueFile as an attribute

    def load(self) -> dict:
        """
        Fetch the queue from the queue json file.

        Returns:
            dict: current queue
        """
        with open(self.queueFile) as queue:
            self.queue = json.load(queue)
            return self.queue

    def flush(self):
        """Dump the queue into the queue json file."""
        with open(self.queueFile, "w") as queue:
            queue.write(json.dumps(self.queue, indent=3))
            return self.queue

    async def setup(self) -> dict:
        """
        Load in queue and set up sniping tasks.

        Returns:
            dict: current queue dict and all pending tasks
        """
        self.load()  # load in the queue from the queue json

        self.pendingSnipes = {}
        for target in self.targets():
            verified = await self.add(
                target, self.queue[target]["offsets"], self.queue[target]["droptime"]
            )
            if bool(verified):
                self.pendingSnipes[target] = verified

        return self.queue, self.pendingSnipes

    def targets(self) -> tuple:
        """
        Get all targets in queue

        Returns:
            tuple: all targets in the queue
        """
        return tuple(self.queue.keys())

    async def add(
        self, target: str, offsets: typing.List[int], droptime: int, override=False
    ) -> bool:
        """
        Add a target to the queue.

        Args:
            target (str): target to add to the queue
            offsets (itterable of two ints): min, max offset for target
            droptime (int): UNIX time of target's drop
            override (bool): skip confirmation/regex checks and just add to queue

        Returns:
            bool: succeeded (True) or failed (False) to add target to the queue
        """

        if (await self.validate(target) is True) or override:
            # if there already is a timestamp from when the target was added to queue, keep it

            if target not in self.queue:
                # create entry for the queue
                self.queue[target] = {
                    "droptime": droptime,
                    "offsets": offsets,
                    "addedAt": time(),
                }

            # dump to queue file
            self.flush()
            # return the task
            return asyncio.create_task(utils.awaitSnipe(target, offsets, droptime))
        else:  # failed to validate target being added to queue
            await self.remove(target)
            return False

    async def remove(self, target: str) -> None:
        """
        Remove a target from the queue.

        Args:
            target (str): target to remove from queue
        """

        if target in self.pendingSnipes:
            # kill pending snipe
            self.pendingSnipes[target].cancel()

            # removed the canceled task
            del self.pendingSnipes[target]
        else:
            logging.warning(
                f'"{target}" was not a pending snipe task, but a removal attempt was initiated'
            )

        # remove target from queue
        del self.queue[target]

        # update the queue file
        self.flush()

    async def validate(
        self,
        target: str,
        testsCheck=True,
        characterCheck=True,
        lengthCheck=True,
        droppingCheck=True,
        tooCloseCheck=True,
    ) -> bool:
        """
        Confirm whether a name can be queued or not, based on invalid characters, dropping status, and length.

        Args:
            target (str): target to validate
            testsCheck (bool): skip all checks if it is detected to be a test snipe
            characterCheck (bool): ensure the characters are all within (a-z, 0-9, _)
            lengthCheck (bool): ensure the target is between 3 and 16 characters
            droppingCheck (bool): ensure the target is dropping
            tooCloseCheck (bool): check if it is too close to the snipe

        Returns:
            bool: target is valid (True) or target is not valid (False)
        """

        if testsCheck:
            # if target is a test snipe then flag it as valid
            if target.lower() in ("test", "testing", "tests"):
                return True

        # check if the target contains invalid characters
        if characterCheck:
            valid = tuple(
                string.ascii_lowercase + string.ascii_uppercase + string.digits + "_"
            )
            for char in target:
                if char not in valid:
                    errorMsg = f'"{target}" contained the invalid character "{char}"'
                    logging.warning(errorMsg)
                    return {"msg": errorMsg, "code": 1, "scheme": "characterCheck"}

        # check if the target is the proper length
        if lengthCheck:
            if not 3 <= len(target) <= 16:
                errorMsg = f'"{target}" is an invalid length ({len(target)})'
                logging.warning(errorMsg)
                return {"msg": errorMsg, "code": 2, "scheme": "lengthCheck"}

        # further checks will require namemc lookup data on the target
        data = await utils.namemc.lookup(target)

        # ensure target is actually dropping
        if droppingCheck:
            if data["status"] != "dropping":
                errorMsg = f'"{target}" is not dropping'
                logging.warning(errorMsg)
                return {"msg": errorMsg, "code": 3, "scheme": "droppingCheck"}

        # check whether target is too close to drop
        if tooCloseCheck:
            if time() + (self.config["general"]["vpsBootTime"] * 60) > data["droptime"]:
                errorMsg = f'"{target}" is too close to dropping'
                logging.warning(errorMsg)
                return {"msg": errorMsg, "code": 4, "scheme": "tooCloseCheck"}

        logging.info(f'"{target}" successfully passed validation')
        # target passed all checks/is safe to queue
        return True
