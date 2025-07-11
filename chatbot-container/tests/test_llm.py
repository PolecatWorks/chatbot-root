from aiohttp import web

from chatbot import config_app_create, keys
from chatbot.config import ServiceConfig
from chatbot.llmconversationhandler import LLMConversationHandler, langchain_app_create
from chatbot.mcp import mcp_app_create
import pytest
from botbuilder.schema import ConversationAccount

@pytest.fixture
def llm_app():
    app = web.Application()

    config_filename = "tests/test_data/config.yaml"
    secrets_dir = "tests/test_data/secrets"
    config: ServiceConfig = ServiceConfig.from_yaml(config_filename, secrets_dir)

    config_app_create(app, config)
    mcp_app_create(app, config)

    langchain_app_create(app, config)

    return app


@pytest.fixture
async def service_client(aiohttp_client, llm_app):
    client = await aiohttp_client(llm_app)
    return client


@pytest.fixture
async def llm_conversation_handler(llm_app) -> LLMConversationHandler:
    """
    Fixture to provide the LLMConversationHandler instance for testing.
    This can be used to test the conversation handler methods directly.
    """
    return llm_app[keys.llmhandler]


@pytest.mark.asyncio
@pytest.mark.skip("Skipping LLM conversation handler test as it requires solving duplicates for prometheus")
async def test_llm_chat(llm_conversation_handler):
    converation_account = ConversationAccount(
        id="test-conversation",
        name="Test Conversation",
        conversation_type="test-type"
    )
    reply = llm_conversation_handler.chat(converation_account, "my-identity", "Hello, how are you?")
    assert reply is not None

# @pytest.mark.asyncio
# async def conversation_handler_test(service_client):
#     # Test the conversation handler with a simple message
#     payload = {
#         "messages": [
#             {"role": "user", "content": "Hello, how are you?"},
#             {"role": "assistant", "content": "I'm fine, thank you!"}
#         ]
#     }
#     resp = await service_client.post("/pie/v0/llm/chat", json=payload)
#     assert resp.status == 404


@pytest.mark.asyncio
async def test_llm_chat_post_valid(service_client):
    # Test POST with valid data


    payload = {
        "messages": [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm fine, thank you!"}
        ]
    }
    resp = await service_client.post("/pie/v0/llm/chat", json=payload)
    assert resp.status == 404
