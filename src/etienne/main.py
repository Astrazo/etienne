import os
from typing import Annotated, Literal

import typer
import webcolors
from dotenv import load_dotenv
from requests import get, post

app = typer.Typer()


@app.command()
def get_instance_services():
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
    for domain in services:
        print(f"\n[{domain['domain']}]")

        for service_name, details in domain["services"].items():
            print(f"\n  {service_name}")
            print(f"    Name: {details.get('name')}")
            print(f"    Description: {details.get('description')}")
            print(f"    Fields: {details.get('fields', {})}")


Effect = Literal[
    "off",
    "candle",
    "fire",
    "prism",
    "sparkle",
    "opal",
    "glisten",
    "underwater",
    "cosmos",
    "sunbeam",
    "enchant",
    "sunrise",
    "sunset",
]


@app.command()
def toggle_light(
    light_id: Annotated[str, typer.Argument()],
    action: Annotated[str, typer.Argument()],
    effect: Annotated[Effect | None, typer.Option("--effect", "-e")] = None,
    colour: Annotated[str | None, typer.Option("--colour", "-c")] = None,
    flash: Annotated[
        Literal["short", "long"] | None, typer.Option("--flash", "-f")
    ] = None,
):

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Build body
    body = {
        "entity_id": f"light.{light_id}",
    }
    if effect is not None:
        body["effect"] = effect
    if colour is not None:
        rgb = webcolors.name_to_rgb(colour)
        body["rgb_color"] = [rgb.red, rgb.green, rgb.blue]
    if flash:
        body["flash"] = flash

    action_request = "turn_on" if action == "on" else "turn_off"
    resp = post(
        f"http://homeassistant.local/api/services/light/{action_request}",
        headers=headers,
        json=body,
    )

    resp.raise_for_status()


@app.command()
def get_status(
    object_type: Annotated[str, typer.Argument()],
    device_id: Annotated[str, typer.Argument()],
):
    headers = {
        "Authorization": f"Bearer {token}",
    }

    entity_id = f"{object_type}.{device_id}"

    resp = get(
        f"http://homeassistant.local/api/states/{entity_id}",
        headers=headers,
    )

    resp.raise_for_status()

    data = resp.json()

    _print_entity_status(data)


def _print_entity_status(data: dict):
    print(f"\nEntity: {data['entity_id']}")
    print(f"State:  {data['state']}")
    print("Attributes:")

    attributes = data.get("attributes", {})

    if not attributes:
        print("  None")
        return

    for key, value in attributes.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("TOKEN")
    app()

    # url = "http://homeassistant.local/api/states/"
    """url = "http://homeassistant.local/api/services/light/turn_off"
    payload = {
        "entity_id": "light.josh_s_office_josh_s_office_light",
        "rgb_color": [255, 100, 0]
    }

    token = os.getenv("TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "content-type": "application/json",
    }
    resp = post(url, headers=headers, json=payload)
    print(resp.text)"""
