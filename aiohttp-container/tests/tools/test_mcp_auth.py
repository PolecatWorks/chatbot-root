import pytest
from unittest.mock import AsyncMock, MagicMock
from aiohttp import web
from customer.tools import authorized_tool, EXPECTED_TOKEN

@pytest.fixture
def mock_request():
    request = MagicMock()
    request.headers = {}
    return request

@authorized_tool
async def sample_tool(request):
    return {"success": True}

@pytest.mark.asyncio
async def test_authorized_tool_with_valid_token(mock_request):
    mock_request.headers["Authorization"] = EXPECTED_TOKEN
    response = await sample_tool(mock_request)
    assert response == {"success": True}

@pytest.mark.asyncio
async def test_authorized_tool_with_missing_token(mock_request):
    response = await sample_tool(mock_request)
    assert response == {"error": "Unauthorized access"}

@pytest.mark.asyncio
async def test_authorized_tool_with_invalid_token(mock_request):
    mock_request.headers["Authorization"] = "Bearer invalidtoken"
    response = await sample_tool(mock_request)
    assert response == {"error": "Unauthorized access"}
