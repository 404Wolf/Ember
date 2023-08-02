import aiofiles
from aiohttp_apispec import docs, json_schema, match_info_schema
import json
from workers import schemas
from time import time
from aiohttp import web


@docs(
    tags=["logs"],
    summary="log offsets from a snipe",
    description="logs offsets from a snipe",
    responses={
        200: {"description": "logged the offsets"},
        422: {"description": "request missing fields"},
    },
)
@json_schema(schemas.logTimes)
async def logTimes(request: web.Request, **kwargs) -> web.Response:
    async with aiofiles.open("logs/times.json") as timesFile:
        times = await timesFile.read()
        times = json.loads(times)

    body = await request.json()

    if body["target"] not in times:
        times[body["target"]] = {"createdAt": time(), "sends": [], "receives": []}

    for send in body["sends"]:  # for each send dict in the body's list of sends
        send["vpsNum"] = body["vpsNum"]  # set the vps number for each send
        times[body["target"]]["sends"].append(send)  # append the rest of the send data
    for receive in body[
        "receives"
    ]:  # for each receive dict in the body's list of receives
        receive["vpsNum"] = body["vpsNum"]  # set the vps number for each receive
        times[body["target"]]["receives"].append(
            receive
        )  # append the rest of the receive data

    times[body["target"]]["receives"] = tuple(
        sorted(times[body["target"]]["receives"], key=lambda send: send["time"])
    )
    times[body["target"]]["sends"] = tuple(
        sorted(times[body["target"]]["sends"], key=lambda receive: receive["time"])
    )

    async with aiofiles.open("logs/times.json", "w") as timesFile:
        await timesFile.write(json.dumps(times, indent=3))

    return web.json_response({"Success": "Offsets have been logged"})


@docs(
    tags=["logs"],
    summary="obtain all send/receive times from a specific snipe",
    description="Get all the send/receive times and data from a specific (previously sniped) target",
    responses={
        200: {"description": "successfully retreived times"},
        404: {"description": "no times found for target"},
    },
)
@match_info_schema(schemas.getLogTimes)
async def getTimes(request: web.Request, **kwargs):
    async with aiofiles.open("logs/times.json") as timesFile:
        times = await timesFile.read()
        times = json.loads(times)

    if request.match_info["target"] not in times:
        return web.json_response(
            {"Error": "No times logs found for target"}, status=404
        )

    return web.json_response(
        {
            "receives": times[request.match_info["target"]]["receives"],
            "sends": times[request.match_info["target"]]["sends"],
        },
    )


@docs(
    tags=["logs"],
    summary="obtain offsets that were used for a given snipe",
    description="return offset data from a specific snipe",
    responses={
        200: {"description": "successfully retreived times"},
        404: {"description": "no times found for target"},
    },
)
@match_info_schema(schemas.getLogTimes)
async def getOffsets(request: web.Request, **kwargs):
    target = request.match_info["target"]

    async with aiofiles.open("logs/offsets.json") as timesFile:
        offsets = await timesFile.read()
        offsets = json.loads(offsets)

    if target in ("*", "all"):
        return web.json_response(offsets)

    if target not in offsets:
        return web.json_response(
            {"Error": "No offset logs found for target"}, status=404
        )

    return web.json_response(offsets[target])


@docs(
    tags=["logs"],
    summary="obtain a list of all past snipes",
    description="Generates a list of all past snipes",
    responses={200: {"description": "successfully retreived list of all past snipes"}},
)
async def snipes(request: web.Request, **kwargs):
    async with aiofiles.open("logs/offsets.json") as timesFile:
        offsets = await timesFile.read()
        offsets = json.loads(offsets)

    offsets = offsets.items()
    offsets = sorted(offsets, key=lambda offset: offset[1]["droptime"], reverse=True)

    return web.json_response(tuple(map(lambda offset: offset[0], offsets)))
