from google import genai

def add_numbers(num1: float, num2: float) -> float:
    """Adds two numbers together.

    Args:
        num1: The first number.
        num2: The second number.

    Returns:
        The sum of the two numbers.
    """
    return num1 + num2


add_numbers_tool_definition = {
    "name": "add_numbers",
    "description": "Adds two numbers together.",
    "parameters": {
        "type": "object",
        "properties": {
            "num1": {
                "type": "number",
                "description": "The first number.",
            },
            "num2": {
                "type": "number",
                "description": "The second number.",
            },
        },
        "required": ["num1", "num2"],
    },
}





# def call_external_api(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
#     """Calls an external API.

#     Args:
#         endpoint: The URL endpoint of the API.
#         method: The HTTP method (e.g., "GET", "POST"). Defaults to "GET".
#         payload: A dictionary of data to send with POST/PUT requests.

#     Returns:
#         A dictionary containing the JSON response from the API.
#     """
#     import requests
#     try:
#         if method.upper() == "GET":
#             response = requests.get(endpoint)
#         elif method.upper() == "POST":
#             response = requests.post(endpoint, json=payload)
#         else:
#             raise ValueError(f"Unsupported HTTP method: {method}")
#         response.raise_for_status()  # Raise an exception for HTTP errors
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f"Error calling API: {e}")
#         return {"error": str(e)}
