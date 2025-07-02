from typing import Annotated, List, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        messages: The list of messages that have been exchanged in the conversation.
    """
    messages: Annotated[List[BaseMessage], add_messages]
