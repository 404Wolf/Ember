from aiohttp_apispec import docs
from aiohttp import web
import utils
from aiohttp_apispec import headers_schema, json_schema
from workers import schemas


@docs(
    tags=["queue"],
    summary="remove a target from the queue",
    description="Remove a target from the queue and from the queue.json",
    responses={
        200: {
            "description": "target was successfully removed from queue",
        },
        422: {"description": "request missing fields"},
        404: {"description": "target was not in queue to begin with"},
    },
)
@headers_schema(schemas.deleteQueue)
async def remove(request: web.Request, queue=None, **kwargs) -> web.Response:
    target = request.headers["target"]

    if target not in queue.targets():
        return web.json_response(
            {
                "Error": "Target not in queue to begin with.",
            },
            status=404,
        )

    await queue.remove(request.headers["target"])

    return web.json_response(
        {
            "Success": "Target was successfully removed from the queue.",
        }
    )


@docs(
    tags=["queue"],
    summary="add a target to the queue",
    description="add a target to the queue and to the queue.json",
    responses={
        200: {
            "description": "target was successfully added to the queue",
        },
        208: {"description": "target is already in queue"},
        400: {"description": "too close to droptime or target is not dropping"},
        422: {"description": "request missing fields"},
    },
)
@json_schema(schemas.postQueue)
async def add(request: web.Request, queue=None, **kwargs) -> web.Response:
    body = await request.json()
    target = body["target"]
    offsets = body["offsets"]

    namemcData = await utils.namemc.lookup(target)
    if ("droptime" in body) and (body["droptime"] != None):
        droptime = body["droptime"]
    else:
        if namemcData["status"] != "dropping":
            return web.json_response(
                {"Error": "Target is not dropping."},
                status=400,
            )
        else:
            droptime = namemcData["droptime"]

    if target in queue.targets():
        return web.json_response(
            {"Error": "Target already in queue."},
            status=208,
        )

    if await queue.add(target, offsets, droptime):
        return web.json_response(
            {
                "Success": "Target was successfully added to the queue.",
            }
        )

    else:
        return web.json_response(
            {
                "Error": "Too close to drop time.",
            },
            status=400,
        )


@docs(
    tags=["queue"],
    summary="retreive the queue",
    description="returns the current queue",
    responses={
        200: {"description": "queue retreived successfully"},
        204: {"description": "no items in queue"},
    },
)
async def fetch(request: web.Request, queue=None, **kwargs) -> web.Response:
    if len(queue.targets()) > 0:
        return web.json_response(queue.queue)
    else:
        return web.Response(status=204)
