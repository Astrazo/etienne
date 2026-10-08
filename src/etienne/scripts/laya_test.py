"""Modern BERT bi-encoder similarity scorer."""

import time

import laya

agent = laya.load("convaiinnovations/laya")

tests = [
    ("Chuck Family Guy on Disney Plus", "tv"),
    ("Turn the TV off", "tv"),
    ("Put the telly on", "tv"),
    ("I want to watch something", "tv"),
    ("Put YouTube on", "tv"),
    ("Kill the bedroom lights", "light"),
    ("Make the office blue", "light"),
    ("It's too dark in here", "light"),
    ("Chuck some Foo Fighters on", "speaker"),
    ("Play Everlong", "speaker"),
    ("Pause the music", "speaker"),
    ("That's way too loud", "speaker"),
]


def classify(text: str):
    start = time.perf_counter()

    result = agent.predict(
        text,
        {
            "device": {
                "type": "choice",
                "instructions": "Which device should handle this request?",
                "criteria": {
                    "light": (
                        "Lighting system. Handles lights, brightness, colours, "
                        "and making a room lighter or darker."
                    ),
                    "speaker": (
                        "Speaker and music system. Handles songs, artists, music "
                        "playback, and audio volume."
                    ),
                    "tv": (
                        "Television system. Handles TV power, shows, movies, "
                        "video, and streaming apps."
                    ),
                },
            }
        },
    )

    elapsed_ms = (time.perf_counter() - start) * 1000

    return result, elapsed_ms


correct = 0
total = len(tests)
for text, expected in tests:
    result, elapsed_ms = classify(text)
    print(result)
    break

    print(f"\n{text}")
    print(f"Expected: {expected}")
    print(f"Time:     {elapsed_ms:.1f} ms")
    print(f"Probabilities:   {result['answers']['device']['probabilities']}")
    print(f"Choice: {result['answers']['device']['choice']}")

    if result["answers"]["device"]["choice"] == expected:
        correct += 1

print("\nResults")
print(f"{correct}/{total}")


# We'll adjust this once we see Laya's exact result structure.
