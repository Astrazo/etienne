"""Chat display and actions, scoped to one open page."""

import asyncio

from fastapi import FastAPI
from loguru import logger
from nicegui import ui

from ..assistant.service import process_utterance


def build_chat(api: FastAPI) -> None:
    pending = False

    def clear_chat():
        conversation.clear()
        welcome.visible = True

    async def send():
        nonlocal pending
        text = (message.value or "").strip()
        if not text or pending:
            return
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
        try:
            async with asyncio.timeout(180):
                result = await process_utterance(
                    text, api.state.home, api.state.ollama_client
                )
            answer = result.get("assistant_response")
            if isinstance(answer, list):
                answer = "\n".join(
                    block if isinstance(block, str) else block.get("text", "")
                    for block in answer
                )
            answer = answer or "No response was returned. Please check the server logs."
        except TimeoutError:
            answer = "The request timed out. An action may still have completed; check your device before retrying."
        except Exception:
            logger.exception("Web chat request failed")
            answer = "Etienne couldn’t complete that request. Check the server and your device before trying again."
        finally:
            pending = False
            send_button.enable()
            new_chat.enable()
            message.enable()
            status.text = ""
        with conversation:
            # NiceGUI escapes message text. Model output is never rendered as HTML.
            ui.chat_message(str(answer), name="Etienne").props(
                "bg-color=grey-10 text-color=grey-2"
            )
        scroll.scroll_to(percent=1)

    with ui.row().classes("page-heading"):
        with ui.column().classes("gap-1"):
            ui.label("Chat").classes("page-title")
            ui.label("What’s on your mind?").classes("muted")
        new_chat = ui.button("New chat", icon="add", on_click=clear_chat).props(
            "outline no-caps"
        )
    with ui.column().classes("chat"):
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
        with (
            ui.scroll_area()
            .classes("conversation")
            .bind_visibility_from(
                welcome, "visible", backward=lambda visible: not visible
            ) as scroll
        ):
            conversation = ui.column().classes("w-full gap-4")
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
        with ui.row().classes("w-full justify-between muted text-xs"):
            ui.label("Messages aren’t saved.")
            ui.label("Enter to send · Shift + Enter for a new line")
        status = ui.label().classes("muted text-xs").props("role=status")
