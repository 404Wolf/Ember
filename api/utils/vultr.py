import aiohttp
import logging
import asyncio


logger = logging.getLogger(__name__)


def filterNull(json: dict) -> dict:
    """
    Remove null dict entries.

    Args:
        json (dict): item to filter null values out of
    """
    # remove all values which are None
    for key, value in tuple(json.items()):
        if value is None:
            del json[key]
    return json


async def listInstances(
    bearer: str, session: aiohttp.ClientSession, tag=None, label=None, main_ip=None
) -> dict:
    """
    List vpses on user's vultr account.

    Args:
        tag: filter results by tag
        label: filter results by label
        main_ip: filter results by main_ip
    """
    json = filterNull({"tag": tag, "label": label, "main_ip": main_ip})

    headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"}

    async with session.get(
        "https://api.vultr.com/v2/instances", headers=headers, params=json
    ) as req:
        req = await req.json()
        if len(req["instances"]) == 0:
            return None
        try:
            return req["instances"]
        except KeyError:
            return req.status


class instance:
    """
    Set up a vultr vps.

    Attributes:
        bearer (str): vultr api token
        label (str): lable for vps
        ip (str): main ip for vps
    """

    def __init__(
        self,
        bearer: str,
        session: aiohttp.ClientSession,
        region=None,
        plan=None,
        osId=None,
        snapshotId=None,
        reservedIpV4=None,
        tag=None,
        label=None,
    ) -> None:
        """
        Set attributes for instance.

        Args:
            bearer (str): vultr api token
            session (aiohttp.ClientSession): aiohttp client session
            region (str): region of vps
            plan (str): vps plan id
            osId (str): id for os to boot vps from
            snapshotId (str): snapshot's id to boot vps from
            reservedIpv4 (str): ip to boot vps as
            tag (str): tag to give vps
            label (str): lable for vps
        """
        self.session = session
        self.region, self.plan = region, plan
        self.osId, self.snapshotId, self.reservedIpv4 = osId, snapshotId, reservedIpV4
        self.tag, self.label = tag, label
        self.headers = {
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        }

    async def create(self) -> dict:
        """
        Create the vps.

        Returns:
            dict: json returned from vultr containing info on the vps
        """
        json = filterNull(
            {
                "region": self.region,
                "plan": self.plan,
                "os_id": self.osId,
                "snapshot_id": self.snapshotId,
                "tag": self.tag,
                "label": self.label,
            }
        )

        async with self.session.post(
            "https://api.vultr.com/v2/instances", headers=self.headers, json=json
        ) as resp:
            await asyncio.sleep(0.025)  # avoid rateliming
            logger.info('Created instance "' + self.label + '"')
            resp = await resp.json()
            self.id = resp["instance"]["id"]
            self.date_created = resp["instance"]["date_created"]
            self.ram = resp["instance"]["ram"]
            return resp["instance"]  # return response dict

    async def data(self) -> dict:
        """
        Gather the data of a vps.

        Returns:
            dict: json returned from vultr containing info on the vps
        """

        async with self.session.get(
            "https://api.vultr.com/v2/instances/" + self.id, headers=self.headers
        ) as resp:
            await asyncio.sleep(0.025)  # avoid rateliming
            resp = await resp.json()
            return resp["instance"]  # return response dict

    async def isReady(self) -> bool:
        """
        Check if vultr has updated the vps' IP address/if the vps is ready.

        Returns:
            bool: vps is ready (True) or vps isn't ready (False)
        """

        async with self.session.get(
            "https://api.vultr.com/v2/instances/" + self.id, headers=self.headers
        ) as resp:
            await asyncio.sleep(0.025)  # avoid rateliming
            try:
                resp = await resp.json()
                resp = resp["instance"]
                if resp["main_ip"] != "0.0.0.0":
                    self.ip = resp[
                        "main_ip"
                    ]  # attempt to set the ip, or raise KeyError if none found
                    return True  # vps is ready
                else:
                    return False  # vps is not ready yet
            except KeyError:
                return False  # vps is not ready yet

    async def destroy(self) -> int:
        """
        Destroy the vps.

        Returns:
            int: status code from instance delete request
        """
        async with self.session.delete(
            "https://api.vultr.com/v2/instances/" + self.id, headers=self.headers
        ) as resp:
            await asyncio.sleep(0.025)  # avoid rateliming
            return resp.status  # return request status
