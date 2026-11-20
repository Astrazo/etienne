"""HTTP adapter for the shared assistant service."""

import asyncio

import httpx
from fastapi import APIRouter, HTTPException, Request
from ollama import ResponseError
from requests.exceptions import RequestException

from ...assistant.service import process_utterance

assistant_router = APIRouter(prefix="/assistant", tags=["Assistant"])


@assistant_router.post("/utterance")
async def handle_utterance(utterance: str, request: Request):
    # Reject blank messages before reading devices or contacting the model.
    utterance = utterance.strip()
    if not utterance:
        raise HTTPException(422, "Utterance must not be empty")

    # Use the same service as NiceGUI, with the same request timeout.
    try:
        async with asyncio.timeout(180):
            response = await process_utterance(
                utterance, request.app.state.home, request.app.state.ollama_client
            )
        return response
    except TimeoutError as error:
        raise HTTPException(
            504, "Assistant request timed out; an action may have completed"
        ) from error
    except (RequestException, httpx.HTTPError, ResponseError, ConnectionError) as error:
        raise HTTPException(502, "Could not complete the assistant request") from error
