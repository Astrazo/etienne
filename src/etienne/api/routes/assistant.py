import json
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request
from requests.exceptions import RequestException

from ...assistant.ollama_client import OllamaClient
from ...assistant.ollama_client.models import add_device_selection
from ...assistant.ollama_client.routes import (
    handle_device_request,
    handle_general_request,
)
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
        QueryClassification = add_device_selection(tuple(device_map))

        # Update home context so the model can see all active devices
        await home.refresh_home_state({"speakers"})

        # If the device type is a speaker, pass in speaker context
        # TODO may need to become a tool request if speaker context is required for non-speaker requests
        home_context = home.get_home_state()

        # Classify the route and whether the user is requesting information.
        classifier_resp = await ollama_client.structured_response_langchain(
            utterance=utterance,
            instructions=f"""
            Classify the user's message. Do not answer it or perform any actions.

            Choose a route:
            - "device": A request about a specific available home device that can
              be identified. Set device to its exact key; clarification_question is null.
            - "general": No specific home device is needed. Set device and
              clarification_question to null.
            - "clarification": A home device is needed but cannot be identified.
              Set device to null and ask a concise question in clarification_question.

            Choose query_classification based on what the user is requesting:
            - "question": Requests factual information or an explanation, even
              without a question mark, such as "Tell me when the next election is".
            - "discussion": Does not request factual information or an explanation,
              such as a greeting, observation, reaction, or instruction to perform an action.
            Merely mentioning a factual topic does not make a statement a question.

            For device selection, an explicit name takes priority. Otherwise use
            home context when it clearly identifies the device, such as the active
            Spotify speaker for "pause the music". Never guess a device. General
            questions about how devices work use the general route.

            Examples:
            - "It's so sunny today!": route "general", query_classification "discussion".
            - "Will it be sunny tomorrow?": route "general", query_classification "question".
            - "Pause the bedroom speaker": route "device" if "speakers:bedroom" is available.
            - "Turn it off" with no clear device in context: route "clarification",
              asking "Which device would you like me to turn off?"

            Available device keys (category:name):
            {json.dumps(list(device_map))}

            Current home context:
            {json.dumps(home_context, indent=2)}
            """,
            format=QueryClassification,
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
            case "general":
                response = await handle_general_request(
                    utterance=utterance, ollama_client=ollama_client
                )
                response["query_classification"] = classifier_resp.query_classification
            case "clarification":
                pass

        response["duration_seconds"] = round(perf_counter() - start_time, 3)
        response["utterance"] = utterance
        return response

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
