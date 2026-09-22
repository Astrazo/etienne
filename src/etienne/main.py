import os

import typer
from dotenv import load_dotenv
from requests import get, post

app = typer.Typer()

@app.command()
def get_instance_services():
    token = os.getenv("TOKEN")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    resp = get(
        "http://homeassistant.local/api/services",
        headers=headers,
    )

    resp.raise_for_status()

    services = resp.json()
    print(services)


if __name__ == "__main__":
    app()
    load_dotenv()
    #url = "http://homeassistant.local/api/states/"
    '''url = "http://homeassistant.local/api/services/light/turn_off"
    payload = {
        "entity_id": "light.living_room_living_room_light_1",
        "rgb_color": [255, 100, 0]
    }

    token = os.getenv("TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "content-type": "application/json",
    }
    resp = post(url, headers=headers, json=payload)
    print(resp.text)'''
