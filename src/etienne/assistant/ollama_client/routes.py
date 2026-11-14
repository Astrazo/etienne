"""Handlers for requests after the model has classified their route."""

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from loguru import logger

from ...devices import ToolProvider
from ...home import Home
from .general_tools import get_general_tools
from .main import OllamaClient


async def handle_general_request(
    utterance: str,
    ollama_client: OllamaClient,
) -> dict[str, Any]:
    model_response = await ollama_client.response_langchain(
        utterance=utterance,
        instructions="""
        Respond to the user's request naturally and concisely.
        Use the provided tools when you need current information or need to perform an action.  
        
        For current or time-sensitive facts—including election dates,
        news, schedules, prices, and public office holders—you must call
        search_web before answering. Do not answer these from memory.
        Prefer official sources and include the supporting source URL.
        Interpret "next" relative to the current local datetime provided in context.
        Do not assume a year in a follow-up search unless the retrieved evidence supports it.
        If search fails or the results do not establish the answer, say you could not
        verify it. Do not replace missing evidence with a guess or a calculation from memory.
        
        Answer directly when a tool is unnecessary.
        
        Base claims about tool actions and retrieved information on successful tool results.
        If something fails or information is missing, explain that clearly.
        """,
        tools=get_general_tools(),
    )

    # Log the evidence the model received, including failures, for troubleshooting.
    for message in model_response["messages"]:
        if isinstance(message, ToolMessage):
            logger.debug(
                "General tool {} result ({}): {}",
                message.name,
                message.status,
                message.content,
            )

    # Get any tool calls
    executed_actions = [
        {
            "function": tool_call["name"],
            "arguments": tool_call["args"],
        }
        for message in model_response["messages"]
        if isinstance(message, AIMessage)
        for tool_call in message.tool_calls
    ]

    return {
        "route": "general",
        "device": None,
        "device_type": None,
        "actions": executed_actions,
        "status": "completed",
        "assistant_response": model_response["messages"][-1].content,
    }


async def handle_clarification_request(
    utterace: str,
) -> dict[str:Any]:
    pass


async def handle_device_request(
    utterance: str,
    device_key: str,
    device: ToolProvider,
    home: Home,
    ollama_client: OllamaClient,
) -> dict[str, Any]:
    """Execute the request using the selected device's tools and return its response."""
    device_type, device_name = device_key.split(":", maxsplit=1)
    tools = device.get_tools()

    model_response = await ollama_client.response_langchain(
        utterance=utterance,
        instructions=f"""
        The device has already been selected.

        Selected device:
        - type: {device_type}
        - name: {device_name}

        All provided tools are bound specifically to this selected device.
        You do not need to specify the device as a tool argument.

        You must call the appropriate provided tool to perform the user's request.
        Respond with a confirmation of what you did for the user in a natural way.
        Preserve the words in user-provided song titles, artist names, album names, and playlist names when constructing tool arguments.
        Treat these names as literal text, including pronouns such as "you" and "me". Do not paraphrase or substitute words.
        You may normalize capitalization and whitespace, and correct clear spelling typos. If uncertain, keep the original wording.
        Base your final response on the actual tool results and preserve the names reported by those tools.
        """,
        tools=tools,
    )

    # Extract what tools were called.
    executed_actions = [
        {
            "function": tool_call["name"],
            "arguments": tool_call["args"],
        }
        for message in model_response["messages"]
        if isinstance(message, AIMessage)
        for tool_call in message.tool_calls
    ]

    # Refresh the shared Spotify state after a speaker action.
    if device_type == "speakers" and executed_actions:
        await home.refresh_home_state({"speakers"})

    return {
        "route": "device",
        "device": device_name,
        "device_type": device_type,
        "actions": executed_actions,
        "status": "completed",
        "assistant_response": model_response["messages"][-1].content,
    }
