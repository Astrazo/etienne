import torch
from transformers import (
    AutoModelForQuestionAnswering,
    AutoTokenizer,
)

MODEL = "distilbert/distilbert-base-cased-distilled-squad"

tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForQuestionAnswering.from_pretrained(MODEL)


tests = [
    # Music
    ("What should be played?", "Play Blackpink on the bedroom speaker"),
    ("What should be played?", "Play Everlong"),
    ("What should be played?", "Chuck some Foo Fighters on"),
    ("What should be played?", "Play Everlong by Foo Fighters in the bedroom"),
    ("What should be played?", "Put some Daft Punk on in the living room"),
    ("What should be played?", "I want to listen to Smells Like Teen Spirit"),
    ("What should be played?", "Can you chuck on The Less I Know the Better"),
    # TV
    ("What show should be played?", "Put Family Guy on Disney Plus"),
    ("What show should be played?", "Play The Simpsons in the living room"),
    ("What show should be played?", "Chuck on Breaking Bad on the bedroom TV"),
    ("What show should be played?", "I want to watch Better Call Saul"),
    # Movies
    ("What movie should be played?", "Put Interstellar on"),
    (
        "What movie should be played?",
        "I want to watch The Dark Knight in the living room",
    ),
    # More conversational phrasing
    ("What should be played?", "Hey Etienne could you put on some Radiohead for me"),
    ("What should be played?", "Can we get a bit of Fleetwood Mac going in here"),
    ("What show should be played?", "Mate chuck Family Guy on for me"),
]


for question, context in tests:
    inputs = tokenizer(
        question,
        context,
        return_tensors="pt",
    )

    with torch.inference_mode():
        outputs = model(**inputs)

    start = outputs.start_logits.argmax()
    end = outputs.end_logits.argmax()

    answer_tokens = inputs["input_ids"][0, start : end + 1]

    answer = tokenizer.decode(
        answer_tokens,
        skip_special_tokens=True,
    )

    print(f"Context:  {context}")
    print(f"Question: {question}")
    print(f"Answer:   {answer}")
    print()
