from chatbot.tools import calcs
from chatbot.tools import customer
from langchain_mcp_adapters.client import MultiServerMCPClient

mytools = [
    calcs.sum_numbers,
    calcs.multiply_numbers,
    customer.search_records_by_name,
    customer.delete_record_by_id,
]


# async def get_mcp_tools():
#     client = MultiServerMCPClient(
#         {
#             # "math": {
#             #     "command": "python",
#             #     # Make sure to update to the full absolute path to your math_server.py file
#             #     "args": ["./examples/math_server.py"],
#             #     "transport": "stdio",
#             # },
#             "customer": {
#                 # make sure you start your weather server on port 8000
#                 "url": "http://localhost:8002/mcp/",
#                 "transport": "streamable_http",
#             }
#         }
#     )
#     tools = await client.get_tools()
#     return tools
