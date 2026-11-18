"""Assistant request handling shared by the HTTP API and NiceGUI."""

import json
from time import perf_counter

from loguru import logger

from ..home import Home
from .ollama_client import OllamaClient
from .ollama_client.models import add_device_selection
from .ollama_client.routes import handle_device_request, handle_general_request


async def process_utterance(
    utterance: str, home: Home, ollama_client: OllamaClient
) -> dict:
    """Process one message. Conversation history is deliberately not supplied."""
    start_time = perf_counter()
    # Build a device map from home, so ollama can see what devices are available
    device_map = home.get_device_map()
    QueryClassification = add_device_selection(tuple(device_map))

    # Read current observations for classification, including changes made outside Etienne.
    home_context = await home.get_home_state()

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

        For lighting requests, select an explicitly identified individual light
        when one is specified. Otherwise, if the room is clearly identified
        and has a light group, select that group—even if it contains only
        one light.

        Use home context when it clearly identifies the target, such as the
        active Spotify speaker for "pause the music". If the target remains
        unclear, ask for clarification. General questions about how devices
        work use the general route.

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

    # Route classification
    match classifier_resp.route:
        case "device":
            device_key = classifier_resp.device
            response = await handle_device_request(
                utterance=utterance,
                device_key=device_key,
                device=device_map[device_key],
                ollama_client=ollama_client,
            )
        case "general":
            response = await handle_general_request(
                utterance=utterance, ollama_client=ollama_client
            )
            response["query_classification"] = classifier_resp.query_classification
        case "clarification":
            response = {
                "route": "clarification",
                "status": "needs_clarification",
                "assistant_response": classifier_resp.clarification_question,
                "actions": [],
            }

    response["duration_seconds"] = round(perf_counter() - start_time, 3)
    response["utterance"] = utterance
    logger.log("INFO", response)
    return response
