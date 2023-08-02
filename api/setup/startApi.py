import utils
import workers
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware
import secrets
from aiohttp import web
import logging
from aiohttp.web import middleware


async def loadEndpoints(app):
    """Inject endpoints into app"""

    app.add_routes(  # logs workers
        [
            web.put("/logs/times", workers.logs.logTimes),
            web.get("/logs/times/{target}", workers.logs.getTimes, allow_head=False),
            web.get(
                "/logs/offsets/{target}", workers.logs.getOffsets, allow_head=False
            ),
            web.get("/logs/snipes", workers.logs.snipes, allow_head=False),
        ]
    )
    app.add_routes(  # lookup workers
        [
            web.get("/namemc/{target}", workers.lookup.namemc, allow_head=False),
        ]
    )
    app.add_routes(  # misc workers
        [
            web.get("/accountGen", workers.misc.accountGen, allow_head=False),
            web.get("/config", workers.misc.config, allow_head=False),
            web.get("/", workers.misc.home),
            web.post("/discord/send", workers.misc.discord),
        ]
    )
    app.add_routes(  # queue workers
        [
            web.get("/queue", workers.queue.fetch, allow_head=False),
            web.delete("/queue", workers.queue.remove),
            web.post("/queue", workers.queue.add),
        ]
    )

    return app


async def startApi(config: dict, queue: utils.queue) -> None:
    """Begin async web server using aiohttp."""

    @middleware
    async def injectData(request, handler):
        """Inject the queue and config into requests as kwargs"""
        normalEndpoints = ("swagger", "api")  # endpoints to not include extra kwargs for
        normalEndpoints = tuple(map(lambda endpoint: endpoint not in str(request.url), normalEndpoints))

        if all(normalEndpoints):
            return await handler(request, config=config, queue=queue)
        return await handler(request)

    # setup app with middlewares
    app = web.Application(
        middlewares=(
            validation_middleware,
            injectData,
        )
    )

    # load the workers
    app = await loadEndpoints(app)

    # enable basic auth
    if "login" not in config["api"]:
        config["api"]["login"] = {
            "username": "admin",
            "password": secrets.token_urlsafe(24),
        }

    # init docs with all parameters, usual for ApiSpec
    setup_aiohttp_apispec(
        app=app,
        title="Ember API Documentation",
        description="Use HTTP basic auth for all requests",
        version="v5",
        url="/api/docs/swagger.json",
        swagger_path="/api/docs",
    )

    # set up the api background task
    runner = web.AppRunner(app)
    await runner.setup()

    # run the api
    site = web.TCPSite(runner, port=config["api"]["port"])
    await site.start()

    # log that the api has booted
    logging.info("Main API has booted.")
    logging.info(
        f"Documentation can be found at http://{config['api']['ip']}:{config['api']['port']}/api/docs"
    )
