
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request
from requests.exceptions import RequestException

from ...assistant.laya_client import LayaClient
from ...assistant.ollama_client import OllamaClient
from ...assistant.ollama_client.models import create_device_selection
from ...home import Home

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
        # Laya classifier
        """device, device_type = await asyncio.to_thread(
            laya_client.select_device, utterance, home
        )"""

        # Build a device map from home, so ollama can see what devices are available
        device_map = home.get_device_map()
        DeviceSelection = create_device_selection(tuple(device_map))

        # Ollama Classifier
        classifier_resp = await ollama_client.response(
            utterance=utterance,
            instructions=(
                "Identify the device the user is referring to. "
                "Select the best matching device type and device name from the "
                "available values. Device types are plural categories: for example, "
                "'speaker' refers to 'speakers', 'TV' refers to 'tvs', and 'light' refers "
                "to 'lights'. Only return null if the request contains no identifiable "
                "device at all."
            ),
            format=DeviceSelection.model_json_schema(),
        )
        selection = DeviceSelection.model_validate_json(classifier_resp.message.content)

        if selection.device is None:
            return {
                "device": None,
                "device_type": None,
                "actions": [],
                "status": "no_matching_device",
            }

        device_key = selection.device
        device_type, device_name = device_key.split(":", maxsplit=1)
        device = device_map[device_key]

        # Grab the tools that the returned device has
        tools = device.get_tools()
        tool_map = {tool.__name__: tool for tool in tools}

        # Pass the tools into Ollama to select function and arguments
        tool_resp = await ollama_client.response(
            utterance=utterance,
            instructions=f"""
            The device has already been selected.

            Selected device:
            - type: {device_type}
            - name: {device.name}

            All provided tools are bound specifically to this selected device.
            You do not need to specify the device as a tool argument.

            You must call the appropriate provided tool to perform the user's request.
            Do not explain the tool choice or respond with text when an appropriate tool exists.
            """,
            tools=tools,
        )
        requested_tools = tool_resp.message.tool_calls

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
        "device": device_name,
        "device_type": device_type,
        "actions": executed_actions,
        "status": "completed",
        "duration_seconds": round(duration, 3),
    }
