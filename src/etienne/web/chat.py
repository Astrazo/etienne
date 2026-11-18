"""Chat display and actions, scoped to one open page."""

import asyncio

from fastapi import FastAPI
from loguru import logger
from nicegui import ui

from ..assistant.service import process_utterance


def build_chat(api: FastAPI) -> None:
    # Track in-flight requests for this open page.
    pending = False

    def clear_chat():
        # Remove the displayed messages and restore the welcome prompts.
        conversation.clear()
        welcome.visible = True

    async def send():
        nonlocal pending

        # Ignore empty messages and repeated submissions while a request runs.
        text = (message.value or "").strip()
        if not text or pending:
            return

        # Lock the composer and show the submitted message immediately.
        pending = True
        send_button.disable()
        new_chat.disable()
        message.disable()
        message.value = ""
        welcome.visible = False
        status.text = "Etienne is working on it…"
        with conversation:
            ui.chat_message(text, sent=True).props("bg-color=grey-9 text-color=grey-2")
        scroll.scroll_to(percent=1)

        # Send this message to the assistant and prepare its response for display.
        try:
            async with asyncio.timeout(180):
                result = await process_utterance(
                    text, api.state.home, api.state.ollama_client
                )
            assistant_response = result.get("assistant_response")
            if isinstance(assistant_response, list):
                response_parts = []
                for block in assistant_response:
                    if isinstance(block, str):
                        response_parts.append(block)
                    else:
                        response_parts.append(block.get("text", ""))
                assistant_response = "\n".join(response_parts)
            assistant_response = (
                assistant_response
                or "No response was returned. Please check the server logs."
            )
        except TimeoutError:
            assistant_response = "The request timed out. An action may still have completed; check your device before retrying."
        except Exception:  # noqa: BLE001 - keep unexpected assistant failures visible in chat
            logger.exception("Web chat request failed")
            assistant_response = "Etienne couldn’t complete that request. Check the server and your device before trying again."
        finally:
            # Restore the composer whether the request succeeded or failed.
            pending = False
            send_button.enable()
            new_chat.enable()
            message.enable()
            status.text = ""

        # Append the reply and bring it into view.
        with conversation:
            # NiceGUI escapes message text. Model output is never rendered as HTML.
            ui.chat_message(str(assistant_response), name="Etienne").props(
                "bg-color=grey-10 text-color=grey-2"
            )
        scroll.scroll_to(percent=1)

    # Page heading and the action to clear the displayed conversation.
    with ui.row().classes("page-heading"):
        with ui.column().classes("gap-1"):
            ui.label("Chat").classes("page-title")
            ui.label("What’s on your mind?").classes("muted")
        new_chat = ui.button("New chat", icon="add", on_click=clear_chat).props(
            "outline no-caps"
        )
    with ui.column().classes("chat"):
        # Welcome text and suggested prompts, shown before the first message.
        with ui.column().classes("chat-welcome") as welcome:
            ui.label("Hey. What’s up?").classes("text-2xl")
            ui.label(
                "Ask a question, or ask me to do something around the house."
            ).classes("muted")
            with ui.row().classes("justify-center"):
                for prompt, label in (
                    ("What can you help me with?", "What can you do?"),
                    ("Which devices can you control?", "What’s connected?"),
                ):
                    ui.button(
                        label, on_click=lambda text=prompt: message.set_value(text)
                    ).props("outline no-caps")

        # Scrollable conversation, visible once the welcome panel is hidden.
        with (
            ui.scroll_area()
            .classes("conversation")
            .bind_visibility_from(
                welcome, "visible", backward=lambda visible: not visible
            ) as scroll
        ):
            conversation = ui.column().classes("w-full gap-4")

        # Message composer and keyboard submission.
        with ui.row().classes("composer"):
            message = (
                ui.textarea(placeholder="Message Etienne…")
                .props(
                    "outlined autogrow maxlength=4000 rows=1 aria-label='Message Etienne'"
                )
                .classes("flex-1")
            )
            message.on("keydown.enter.exact.prevent", send)
            send_button = (
                ui.button(icon="arrow_upward", on_click=send)
                .props("unelevated text-color=black aria-label=Send")
                .mark("send-message")
            )

        # Usage hints and request progress.
        with ui.row().classes("w-full justify-between muted text-xs"):
            ui.label("Messages aren’t saved.")
            ui.label("Enter to send · Shift + Enter for a new line")
        status = ui.label().classes("muted text-xs").props("role=status")
