import asyncio

from fastapi import APIRouter, HTTPException, Request
from requests.exceptions import RequestException

from ...assistant.laya_client import LayaClient
from ...assistant.ollama_client import OllamaClient
from ...home import Home

from time import perf_counter

assistant_router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"],
)


@assistant_router.post("/utterance")
async def handle_utterance(utterance: str, request: Request):
    home: Home = request.app.state.home
    laya_client: LayaClient = request.app.state.laya_client
    ollama_client: OllamaClient = request.app.state.ollama_client
    start_time = perf_counter()
    try:
        device, device_type = await asyncio.to_thread(
            laya_client.select_device, utterance, home
        )

        # Grab the tools that the returned device has
        tools = device.get_tools()
        tool_map = {tool.__name__: tool for tool in tools}

        # Pass the tools into Ollama to select function and arguments
        ollama_response = await ollama_client.response(
            utterance=utterance,
            tools=tools,
        )
        requested_tools = ollama_response.message.tool_calls

        # Map the names of the tools do their actual function for calling
        tool_map = {tool.__name__: tool for tool in tools}

        executed_actions = []
        for tool_call in requested_tools or []:
            # Extrac the name and arguments
            function_name = tool_call.function.name
            arguments = tool_call.function.arguments

            if function_name not in tool_map:
                raise HTTPException(
                    status_code=500,
                    detail=f"Model requested unknown tool: {function_name}",
                )

            # Grab the actual callable and call it with arguments
            # TODO UNCOMMENT TO ACTUALLY CALL FUNCTIONS
            function = tool_map[function_name]
            await function(**arguments)

            # Append for loggin
            executed_actions.append(
                {
                    "function": function_name,
                    "arguments": arguments,
                }
            )

    except RequestException as error:
        raise HTTPException(
            status_code=502, detail="Could not form plan using Laya"
        ) from error
    duration = perf_counter() - start_time
    return {
        "device": device.name,
        "device_type": device_type,
        "actions": executed_actions,
        "status": "completed",
        "duration_seconds": round(duration, 3)
    }
