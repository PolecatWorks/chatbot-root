import pytest
from unittest.mock import AsyncMock, MagicMock
from chatbot.mcp import AuthorizedMultiServerMCPClient # Assuming this is the correct import path

@pytest.fixture
def mock_mcp_client():
    # This mock needs to be more sophisticated if we want to test the actual request sending
    # For now, it just allows us to instantiate the AuthorizedMultiServerMCPClient
    mock_client = MagicMock()
    mock_client._request = AsyncMock()
    return mock_client

@pytest.mark.asyncio
async def test_authorized_client_adds_auth_header(mock_mcp_client):
    # This test is a bit basic as we're not actually sending a request.
    # It primarily checks that the _request method is called with the Authorization header.

    # To make this test more robust, we would need to mock the underlying HTTP client
    # and verify that the header is correctly passed to it.

    # Create an instance of the client, it will use the mocked _request
    # We need to pass a dummy config for the client
    client = AuthorizedMultiServerMCPClient(servers_config={"server1": {"url": "http://localhost", "transport": "http"}})

    # Replace the real _request with our mock for this instance
    client._request = mock_mcp_client._request

    await client._request("GET", "server1", "/some/path")

    # Check that _request was called with the Authorization header
    mock_mcp_client._request.assert_called_once_with(
        "GET",
        "server1",
        "/some/path",
        headers={"Authorization": "Bearer mytoken"}
    )
