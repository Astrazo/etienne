"""HTTP adapter for the shared assistant service."""

from fastapi import APIRouter, HTTPException, Request
from requests.exceptions import RequestException

from ...assistant.service import process_utterance

assistant_router = APIRouter(prefix="/assistant", tags=["Assistant"])


@assistant_router.post("/utterance")
async def handle_utterance(utterance: str, request: Request):
    try:
        response = await process_utterance(
            utterance, request.app.state.home, request.app.state.ollama_client
        )
        return response
    except RequestException as error:
        raise HTTPException(502, "Could not complete the assistant request") from error
