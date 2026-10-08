from ollama import AsyncClient, ChatResponse


class OllamaClient:
    def __init__(
        self,
        model: str,
        system_prompt: str,
        reasoning: bool = False,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.reasoning = reasoning
        self.client = AsyncClient()

    async def response(
        self,
        utterance: str,
        tools: list | None = None,
        format: str | dict | None = None,
    ) -> ChatResponse:
        return await self.client.chat(
            model=self.model,
            think=self.reasoning,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": utterance,
                },
            ],
            tools=tools,
            format=format,
        )
