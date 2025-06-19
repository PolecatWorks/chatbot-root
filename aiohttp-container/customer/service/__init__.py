import asyncio
import logging



from customer.service.state import Events
from customer.hams import Hams, hams_app_create
from customer.config import ServiceConfig
from customer.service.webview import ChunkView

from customer import keys
from aiohttp import web
from datetime import datetime, timezone

from prometheus_client import CollectorRegistry



logger = logging.getLogger(__name__)


async def service_coroutine(app: web.Application):
    """
    Coroutine for the service
    """
    logger.info("Service: coroutine start")

    while True:
        waitTime = app[keys.events].updateChunk(datetime.now(timezone.utc))

        await asyncio.sleep(waitTime)


async def service_coroutine_cleanup(app: web.Application):
    """
    Launch the coroutine as a cleanup task
    """

    app[keys.coroutine] = asyncio.create_task(service_coroutine(app))

    logger.info("Service: coroutine running")
    yield

    app[keys.coroutine].cancel()

    logger.info("Service: coroutine cleanup")


def service_app_create(app: web.Application, config: ServiceConfig) -> web.Application:
    """
    Create the service with the given configuration file
    """

    app[keys.config] = config
    app[keys.events] = Events(app[keys.config].events, datetime.now(timezone.utc), 0)

    app.cleanup_ctx.append(service_coroutine_cleanup)

    app.add_routes([web.view(f"/{config.webservice.prefix}/chunks", ChunkView)])

    app[keys.webservice] = app

    logger.info(
        f"Service: {app[keys.config].webservice.url.host}:{app[keys.config].webservice.url.port}/{app[keys.config].webservice.prefix}"
    )

    return app
