import spotipy


class SpotifyClient:
    def __init__(self, spotify: spotipy.Spotify):
        self.spotify = spotify

    async def find_device(self, name: str):
        pass

    async def find_track(
        self,
        song: str,
        artist: str | None = None,
    ):
        pass