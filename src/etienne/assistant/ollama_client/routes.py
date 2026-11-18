"""Handlers for requests after the model has classified their route."""

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from loguru import logger

from ...devices import Device
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
        Do not include unecessary information that doesn't relate directly to the users request.
        
        Use the provided tools when you need current information or need to perform an action. 

        When answering information queries, know that you are operating under a knowledge cut of about 2 years.  
        Therefore, to keep your knowledge present and factual, use the web_search tool to fact check your
        answers before responding if relevant.  For every one of these information queries, you must return your sources from the web.

        User terms like "next", "previous" should be based on the current date.  If the user asks for the "next"
        anything, you cannot return information regarding dates prior to the current date.
        
        For current, temporal, or time-sensitive facts—including event dates,
        latest news, schedules, prices, general current affairs, you must call
        web_search before answering. Do not answer these from memory.

        If an authoritative source explicitly states that information is
        unannounced, unconfirmed, or unknown, report that with a citation.

        If the retrieved evidence does not establish an answer, say you could
        not verify it. Do not invent missing details or treat missing search
        results as proof that something does not exist or has not happened.
        
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
    device: Device,
    ollama_client: OllamaClient,
) -> dict[str, Any]:
    """Execute the request using the selected device's tools and return its response."""
    device_type, selected_device_key = device_key.split(":", maxsplit=1)
    tools = device.get_tools()

    model_response = await ollama_client.response_langchain(
        utterance=utterance,
        instructions=f"""
        The device has already been selected.

        Selected device:
        - type: {device_type}
        - key: {selected_device_key}

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

    return {
        "route": "device",
        "device": selected_device_key,
        "device_type": device_type,
        "actions": executed_actions,
        "status": "completed",
        "assistant_response": model_response["messages"][-1].content,
    }
