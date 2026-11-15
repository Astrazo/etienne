from typing import Any

from langchain.agents import create_agent
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from ollama import AsyncClient, ChatResponse
from pydantic import BaseModel

from .middleware import add_dynamic_context, handle_tool_errors
from .models import QueryClassification


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
            middleware=[handle_tool_errors, add_dynamic_context],
        )

        response = await agent.ainvoke(
            {
                "messages": [
                    HumanMessage(content=utterance),
                ]
            }
        )

        return response

    # This funciton is needed as we found a limitation with structured responses with tool calls inside
    # create_agent.  If we need a structured output, pass messages into here
    async def structured_response_langchain(
        self,
        instructions: str,
        format: type[BaseModel] | dict[str, Any],
        utterance: str | None = None,
        agent_result: dict[str, Any] | None = None,
    ) -> QueryClassification:
        """Generate validated output, allowing up to three retries with feedback."""
        # These instructions belong to this formatting step, rather than the agent.
        messages: list[BaseMessage] = [SystemMessage(content=instructions)]

        # Build messages to be formatted
        if agent_result is not None:
            messages.extend(agent_result["messages"])
            messages.append(
                HumanMessage(
                    content="Produce the structured response from the conversation and tool results above."
                )
            )
        elif utterance is not None:
            messages.append(HumanMessage(content=utterance))

        model = ChatOllama(model=self.model, reasoning=self.reasoning)
        structured_model = model.with_structured_output(
            format,
            method="json_schema",
        )
        max_retries = 3
        for retry in range(max_retries + 1):
            try:
                # This runs pydantic model_validate on the output because of the above setup
                return await structured_model.ainvoke(messages)
            except OutputParserException as error:
                if retry == max_retries:
                    raise

                # Keep the rejected output so the model can correct its own response.
                if error.llm_output is not None:
                    messages.append(AIMessage(content=error.llm_output))
                messages.append(
                    HumanMessage(
                        content=(
                            "Your previous response failed validation against the required schema.\n"
                            f"Validation feedback: {error}\n"
                            "Return a corrected response that satisfies the schema and "
                            "the original request."
                        )
                    )
                )
