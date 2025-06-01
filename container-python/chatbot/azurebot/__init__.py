# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount
from botbuilder.schema import Activity, ActivityTypes
from aiohttp import web
from chatbot import keys

from datetime import datetime
import traceback
import logging

from chatbot.config import ServiceConfig

from botbuilder.core import (
    BotFrameworkAdapterSettings,
    BotFrameworkAdapter,
    TurnContext,
)
from chatbot.azurebot.webview import AzureBotView
from prometheus_client import CollectorRegistry, Summary

# Set up logging
logger = logging.getLogger(__name__)


# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    logger.error(f"\n [on_turn_error] unhandled error: {error}")
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity, which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)


class AzureBot(ActivityHandler):
    """
    AzureBot is a bot that handles incoming messages and responds using an AI model.
    """

    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    def __init__(self, app: web.Application, prometheus_registry: CollectorRegistry):
        super().__init__()
        self.app = app
        self.chat_metric = Summary(
            "chat_usage",
            "Summary of Chat actions",
            ["action"],
            registry=prometheus_registry,
        )

    async def on_message_activity(self, turn_context: TurnContext):

        with self.chat_metric.labels("on_message").time():
            llm_reply = await self.app[keys.myai].chat(
                turn_context.activity.conversation, turn_context.activity.text
            )

        logger.debug("LLM reply: %s", llm_reply)
        await turn_context.send_activity(llm_reply)

    async def on_members_added_activity(
        self, members_added: ChannelAccount, turn_context: TurnContext
    ):
        with self.chat_metric.labels("on_members_added").time():
            for member_added in members_added:
                if member_added.id != turn_context.activity.recipient.id:
                    await turn_context.send_activity("Hello and welcome!")


def azure_app_create(
    app: web.Application, config: ServiceConfig, prometheus_registry: CollectorRegistry
) -> web.Application:
    """
    Create the service with the given configuration file
    """
    # Add the bot settings and adapter to the app
    app[keys.botsettings] = BotFrameworkAdapterSettings(
        config.bot.app_id, config.bot.app_password.get_secret_value()
    )
    app[keys.botadapter] = BotFrameworkAdapter(app[keys.botsettings])

    app[keys.botadapter].on_turn_error = on_error

    app[keys.bot] = AzureBot(app, prometheus_registry)

    app.add_routes([web.view(config.bot.api_path, AzureBotView)])
    logger.info(
        f"Bot: {app[keys.config].webservice.url.host}:{app[keys.config].webservice.url.port}{app[keys.config].bot.api_path}"
    )
    return app
