import laya

agent = laya.load("convaiinnovations/laya")  

result = agent.predict(
    "Chuck Family Guy on Disney Plus",
    {
        "device_type": {
            "type": "choice",
            "instructions": "Which device type should handle this request?",
            "criteria": {
                "light": "Lighting, brightness, colours, making rooms lighter or darker.",
                "speaker": "Music, songs, artists, audio playback and audio volume.",
                "tv": "TV, shows, movies, video and streaming applications.",
            },
        }
    },
)

print(result)