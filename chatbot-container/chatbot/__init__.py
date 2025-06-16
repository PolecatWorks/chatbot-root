
from aiohttp import web
from chatbot.config import ServiceConfig
from pydantic_yaml import to_yaml_str
import logging
from chatbot.hams import Hams, hams_app_create
from chatbot.service import service_app_create
from chatbot.azurebot import azure_app_create
from .mcp import mcp_app_create
from chatbot.llmconversationhandler import langchain_app_create
from chatbot import keys

logger = logging.getLogger(__name__)


def app_init(app: web.Application, config: ServiceConfig):
    """
    Initialize the service with the given configuration file
    This is seperated from service_init as it is also used from the adev dev server
    """

    logger.info(f"CONFIG\n{to_yaml_str(config, indent=2)}")

    hams_app_create(app, config.hams)
    mcp_app_create(app,config)
    service_app_create(app, config)
    azure_app_create(app, config)

    langchain_app_create(app, config)

    return app


def app_start(config: ServiceConfig):
    """
    Start the service with the given configuration file
    """
    app = web.Application()

    app_init(app, config)

    web.run_app(
        app,
        host=app[keys.config].webservice.url.host,
        port=app[keys.config].webservice.url.port,
        # TODO: Review the custom logging and replace into config
        access_log_format='%a "%r" %s %b "%{Referer}i" "%{User-Agent}i"',
        access_log=logger,
    )

    logger.info(f"Service stopped")
