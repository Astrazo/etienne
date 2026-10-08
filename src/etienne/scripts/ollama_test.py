from ollama import chat

response = chat(
    model="qwen3.5:latest",
    messages=[
        {
            "role": "user",
            "content": "Play Blackpink on the bedroom speaker",
        }
    ],
    tools=[""],
    think=False,
)

print(response)
