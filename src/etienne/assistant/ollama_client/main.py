from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from loguru import logger
from ollama import AsyncClient, ChatResponse
from pydantic import BaseModel


class OllamaClient:
    def __init__(
        self,
        model: str,
        system_prompt: str = False,
        reasoning: bool = False,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.reasoning = reasoning
        self.client = AsyncClient()

    async def response(
        self,
        utterance: str,
        instructions: str,
        tools: list | None = None,
        format: str | dict | None = None,
    ) -> ChatResponse:
        response = await self.client.chat(
            model=self.model,
            think=self.reasoning,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": f"{instructions}\n\nUser request:\n{utterance}",
                },
            ],
            tools=tools,
            format=format,
        )
        print()
        print(response)
        return response

    async def response_langchain(
        self,
        utterance: str,
        instructions: str,
        tools: list | None = None,
        format: str | dict | None = None,
    ):

        # Create agent, might go into init at some point
        agent = create_agent(
            model=ChatOllama(model=self.model, reasoning=self.reasoning),
            system_prompt=f"{self.system_prompt}\n\n{instructions}",
            tools=tools,
            response_format=format,
            middleware=[self._handle_tool_errors]
        )

        response = await agent.ainvoke({
            "messages": [
                HumanMessage(content=utterance),
            ]
        })

        return response

    @staticmethod
    @wrap_tool_call
    async def _handle_tool_errors(
        request: ToolCallRequest, 
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]]):
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

    # This funciton is needed as we found a limitation with structured responses with tool calls inside
    # create_agent.  If we need a structured output, pass messages into here
    async def structured_response_langchain(
        self,
        instructions: str,
        format: type[BaseModel] | dict[str, Any],
        utterance: str | None = None,
        agent_result: dict[str, Any] | None = None,
    ): 
        # These instructions belong to this formatting step, rather than the agent.
        messages: list[BaseMessage] = [SystemMessage(content=instructions)]

        # Build messages to be formatted
        if agent_result is not None:
            messages.extend(agent_result["messages"])
            messages.append(HumanMessage(
                content="Produce the structured response from the conversation and tool results above."
            ))
        elif utterance is not None:
            messages.append(HumanMessage(content=utterance))
        
        model = ChatOllama(model=self.model, reasoning=self.reasoning)
        structured_model = model.with_structured_output(
            format,
            method="json_schema",
        )
        return await structured_model.ainvoke(messages)