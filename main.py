import os
from typing import Annotated, Literal

import spotipy
import typer
import webcolors
from dotenv import load_dotenv
from requests import get, post
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

app = typer.Typer()

lights_app = typer.Typer()
spotify_app = typer.Typer()

app.add_typer(lights_app, name="lights")
app.add_typer(spotify_app, name="spotify")


HOME_ASSISTANT_URL = "http://homeassistant.local"
HOME_ASSISTANT_TOKEN = os.getenv("TOKEN")

DEVICE_ALIASES = {
    "living_room_soundbar": "c2f34440bf4982af8a18286dcf308c48dfb7b416",
}


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

RepeatMode = Literal["off", "track", "context"]


# ---------------------------------------------------------------------------
# Home Assistant helpers
# ---------------------------------------------------------------------------


def _home_assistant_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
        "Content-Type": "application/json",
    }


def _print_entity_status(data: dict) -> None:
    print(f"\nEntity: {data['entity_id']}")
    print(f"State:  {data['state']}")
    print("Attributes:")

    attributes = data.get("attributes", {})

    if not attributes:
        print("  None")
        return

    for key, value in attributes.items():
        print(f"  {key}: {value}")


# ---------------------------------------------------------------------------
# Home Assistant commands
# ---------------------------------------------------------------------------


@app.command()
def services():
    resp = get(
        f"{HOME_ASSISTANT_URL}/api/services",
        headers=_home_assistant_headers(),
    )
    resp.raise_for_status()

    for domain in resp.json():
        print(f"\n[{domain['domain']}]")

        for service_name, details in domain["services"].items():
            print(f"\n  {service_name}")
            print(f"    Name: {details.get('name')}")
            print(f"    Description: {details.get('description')}")
            print(f"    Fields: {details.get('fields', {})}")


@app.command()
def status(
    object_type: Annotated[str, typer.Argument()],
    device_id: Annotated[str, typer.Argument()],
):
    entity_id = f"{object_type}.{device_id}"

    resp = get(
        f"{HOME_ASSISTANT_URL}/api/states/{entity_id}",
        headers=_home_assistant_headers(),
    )
    resp.raise_for_status()

    _print_entity_status(resp.json())


@lights_app.command()
def set(
    light_id: Annotated[str, typer.Argument()],
    action: Annotated[Literal["on", "off"], typer.Argument()],
    effect: Annotated[Effect | None, typer.Option("--effect", "-e")] = None,
    colour: Annotated[str | None, typer.Option("--colour", "-c")] = None,
    flash: Annotated[
        Literal["short", "long"] | None,
        typer.Option("--flash", "-f"),
    ] = None,
):
    body = {
        "entity_id": f"light.{light_id}",
    }

    if effect is not None:
        body["effect"] = effect

    if colour is not None:
        rgb = webcolors.name_to_rgb(colour)
        body["rgb_color"] = [rgb.red, rgb.green, rgb.blue]

    if flash is not None:
        body["flash"] = flash

    resp = post(
        f"{HOME_ASSISTANT_URL}/api/services/light/turn_{action}",
        headers=_home_assistant_headers(),
        json=body,
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Spotify helpers
# ---------------------------------------------------------------------------


def _spotify_client() -> spotipy.Spotify:
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope=(
                "user-read-playback-state "
                "user-modify-playback-state "
                "playlist-read-private"
            ),
        )
    )


def _find_device(
    spotify: spotipy.Spotify,
    name: str,
) -> dict | None:
    target_id = DEVICE_ALIASES.get(name.lower(), name)

    for device in spotify.devices()["devices"]:
        if device["id"] == target_id:
            return device

    return None


def _get_device(
    spotify: spotipy.Spotify,
    name: str,
) -> dict:
    device = _find_device(spotify, name)

    if device is None:
        raise typer.BadParameter(f"Spotify device not found: {name}")

    return device


def _find_track(
    spotify: spotipy.Spotify,
    song: str,
    artist: str | None = None,
) -> dict | None:
    query = f'track:"{song}"'

    if artist:
        query += f' artist:"{artist}"'

    results = spotify.search(
        q=query,
        type="track",
        limit=1,
    )

    tracks = results["tracks"]["items"]

    if not tracks:
        return None

    return tracks[0]


# ---------------------------------------------------------------------------
# Spotify commands
# ---------------------------------------------------------------------------


@spotify_app.command()
def devices():
    spotify = _spotify_client()

    for device in spotify.devices()["devices"]:
        print(
            f"{device['name']} "
            f"({device['type']}) "
            f"id={device['id']} "
            f"active={device['is_active']}"
        )


@spotify_app.command("play")
def play(
    device: Annotated[str, typer.Argument()],
    song: Annotated[str | None, typer.Option("--song", "-s")] = None,
    artist: Annotated[str | None, typer.Option("--artist", "-a")] = None,
):
    spotify = _spotify_client()
    spotify_device = _get_device(spotify, device)

    if song is None:
        spotify.start_playback(
            device_id=spotify_device["id"],
        )
        return

    track = _find_track(
        spotify,
        song=song,
        artist=artist,
    )

    if track is None:
        raise typer.BadParameter(f"Track not found: {song}")

    spotify.start_playback(
        device_id=spotify_device["id"],
        uris=[track["uri"]],
    )


@spotify_app.command("pause")
def pause(
    device: Annotated[str, typer.Argument()],
):
    spotify = _spotify_client()
    spotify_device = _get_device(spotify, device)

    spotify.pause_playback(
        device_id=spotify_device["id"],
    )


@spotify_app.command("next")
def next_track(
    device: Annotated[str, typer.Argument()],
):
    spotify = _spotify_client()
    spotify_device = _get_device(spotify, device)

    spotify.next_track(
        device_id=spotify_device["id"],
    )


@spotify_app.command("prev")
def previous_track(
    device: Annotated[str, typer.Argument()],
):
    spotify = _spotify_client()
    spotify_device = _get_device(spotify, device)

    spotify.previous_track(
        device_id=spotify_device["id"],
    )


@spotify_app.command()
def volume(
    device: Annotated[str, typer.Argument()],
    value: Annotated[int, typer.Argument(min=0, max=100)],
):
    spotify = _spotify_client()
    spotify_device = _get_device(spotify, device)

    spotify.volume(
        volume_percent=value,
        device_id=spotify_device["id"],
    )


@spotify_app.command()
def shuffle(
    device: Annotated[str, typer.Argument()],
    enabled: Annotated[bool, typer.Argument()],
):
    spotify = _spotify_client()
    spotify_device = _get_device(spotify, device)

    # Ensure repeat isn't on if turning shuffle on
    if enabled:
        spotify.repeat(
            state="off",
            device_id=spotify_device["id"],
        )

    spotify.shuffle(
        state=enabled,
        device_id=spotify_device["id"],
    )


@spotify_app.command()
def repeat(
    device: Annotated[str, typer.Argument()],
    mode: Annotated[RepeatMode, typer.Argument()],
):
    spotify = _spotify_client()
    spotify_device = _get_device(spotify, device)

    spotify.repeat(
        state=mode,
        device_id=spotify_device["id"],
    )


if __name__ == "__main__":
    app()
