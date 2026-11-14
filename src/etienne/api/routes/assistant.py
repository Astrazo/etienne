import json
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request
from requests.exceptions import RequestException

from ...assistant.ollama_client import OllamaClient
from ...assistant.ollama_client.models import create_device_selection
from ...assistant.ollama_client.routes import handle_device_request, handle_general_request
from ...home import Home

assistant_router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"],
)


@assistant_router.post("/utterance")
async def handle_utterance(utterance: str, request: Request):
    home: Home = request.app.state.home
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

        # Update home context so the model can see all active devices
        await home.refresh_home_state({"speakers"})

        # If the device type is a speaker, pass in speaker context
        # TODO may need to become a tool request if speaker context is required for non-speaker requests
        home_context = home.get_home_state()

        # Ollama Device Classifier
        classifier_resp = await ollama_client.structured_response_langchain(
            utterance=utterance,
            instructions=f"""
            Classify the user's request using one of three routes:

            - "device": The request applies to an available device and you can
              identify which one. Set device to its exact available key and
              clarification_question to null.
            - "general": The request does not require selecting a home device,
              such as a weather question or general conversation. Set device
              and clarification_question to null. Do not answer the request.
            - "clarification": The request requires a device, but the intended
              device is missing, ambiguous, or unavailable. Set device to null
              and clarification_question to a concise question that asks which
              available device the user intends. Do not invent a device key.

            Available devices are represented using the format "category:name", where
            categories are plural. For example:

            - "speakers:bedroom"
            - "tvs:living_room"
            - "lights:office"

            Available device keys:
            {json.dumps(list(device_map))}

            Use the current home context when the user refers to an active device without
            giving its name. For example, requests such as "pause the music", "skip this
            song", or "what is playing?" refer to the active Spotify speaker.

            An explicitly named device always takes priority over the active device.

            Use the "device" route only when the available devices and current
            home context identify the intended device. Do not choose an arbitrary
            device when the context is ambiguous. General questions about devices
            do not require selecting one unless they concern a specific home device.

            Examples:
            - "Pause the bedroom speaker": route "device", selecting
              "speakers:bedroom" if it is available.
            - "What's the weather?": route "general".
            - "Turn it off" with no clear device in context: route "clarification",
              asking "Which device would you like me to turn off?"

            Current home context:

            {json.dumps(home_context, indent=2)}
            """,
            format=DeviceSelection,
        )
        print()
        print(home_context)

        # Route classification
        match classifier_resp.route:
            case "device":
                device_key = classifier_resp.device
                response = await handle_device_request(
                    utterance=utterance,
                    device_key=device_key,
                    device=device_map[device_key],
                    home=home,
                    ollama_client=ollama_client,
                )
                
                # Return
                return response
            case "general":
                response = await handle_general_request(
                    utterance=utterance,
                    ollama_client=ollama_client
                )
                response["duration_seconds"] = round(perf_counter() - start_time, 3)
                return response
            case "clarification":
                pass

    except RequestException as error:
        raise HTTPException(
            status_code=502, detail="Could not form plan using Laya"
        ) from error

    # Preserve the existing fallback until the other routes are implemented.
    return {
        "device": None,
        "device_type": None,
        "actions": [],
        "status": "no_matching_device",
    }
