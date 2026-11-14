from collections.abc import Awaitable, Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
    wrap_model_call,
    wrap_tool_call,
)
from langchain.messages import SystemMessage, ToolMessage
from loguru import logger


@wrap_model_call
async def add_dynamic_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
) -> ModelResponse:
    # Build current time context
    timezone = ZoneInfo("Australia/Sydney")
    now = datetime.now(timezone)
    time_context = (
        f"Current local datetime: {now.isoformat()}\n"
        f"User timezone: {timezone.key}\n"
        "Interpret times without an explicit timezone in the user's timezone."
    )

    # Grab the existing context and append the dynamic context
    content = list(request.system_message.content_blocks)
    content.append({"type": "text", "text": time_context})

    # Return new system message
    system_message = SystemMessage(content=content)
    return await handler(request.override(system_message=system_message))


@wrap_tool_call
async def handle_tool_errors(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]],
):
    """Convert tool exceptions into ToolMessages the model can react to."""
    try:
        return await handler(request)
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "Tool {} failed",
            request.tool_call["name"],
        )
        return ToolMessage(
            content=(
                f"Tool failed with {type(e).__name__}: {e}. "
                "The action may have partially completed."
            ),
            tool_call_id=request.tool_call["id"],
            status="error",
        )
