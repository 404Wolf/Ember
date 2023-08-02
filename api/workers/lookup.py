from aiohttp_apispec import docs
import utils
from aiohttp import web
from aiohttp_apispec import docs, match_info_schema
from workers import schemas


@docs(
    tags=["lookup"],
    summary="scrape NameMC for data on a username",
    description="Sends a discord message with the content https://namemc.com/search?q=<name>, and scrapes/parses the embed.\n"
    + "Make the endpoint /namemc/\{target\} to select a target to get data for",
    responses={200: {"description": "successfully retreived NameMC data"}},
)
@match_info_schema(schemas.getNameMC)
async def namemc(request: web.Request, **kwargs) -> web.Response:
    return web.json_response(await utils.namemc.lookup(request.match_info["target"]))
