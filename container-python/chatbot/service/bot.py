
from aiohttp import web
from aiohttp.web import Response, json_response, Request
from chatbot.service.state import Events
from pydantic import BaseModel, ValidationError
import logging
from botbuilder.schema import Activity, ActivityTypes
from chatbot import keys

# Set up logging
logger = logging.getLogger(__name__)




class MessageView(web.View):

    async def post(self) -> Response:

        req: Request = self.request

        # Main bot message handler.
        logger.debug(f"Received request: {req}")
        if "application/json" in req.headers["Content-Type"]:
            body = await req.json()
        else:
            return Response(status=415)

        activity = Activity().deserialize(body)
        auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""
        logger.debug(f"Activity: {activity}")



        response = await req.app[keys.botadapter].process_activity(activity, auth_header, req.app[keys.bot].on_turn)
        logger.debug(f"Response: {response}")
        if response:
            return json_response(data=response.body, status=response.status)
        return Response(status=201)
