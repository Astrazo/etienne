"""Controls playback on a speaker."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, Field, validate_call

from ..integrations import HomeAssistantClient, SpotifyClient
from .models import SpeakerState, TrackInput


class Speaker:
    """Controls music playback on a speaker."""

    def __init__(
        self,
        name: str,
        spotify_id: str,
        spotify_client: SpotifyClient,
        db_path: Path,
        ha_entity_id: str | None = None,
        ha_client: HomeAssistantClient | None = None,
    ):
        self.name = name
        self.ha_entity_id = ha_entity_id
        self.ha_client = ha_client
        self.spotify_id = spotify_id
        self.spotify_client = spotify_client
        self.db_path = db_path

    @validate_call
    async def play_tracks(
        self,
        tracks: list[TrackInput],
    ) -> str:
        """Play one or more specific tracks.

        Args:
            tracks (list[TrackInput]): Tracks to play, including each track name and optional artist.
        """

        spotify_tracks = [(track.song, track.artist) for track in tracks]
        result = await asyncio.to_thread(
            self.spotify_client.play_tracks,
            self.spotify_id,
            spotify_tracks,
        )

        # Build a list of found track names
        found_track_names = []
        for track in result["found_tracks"]:
            track_name = track["name"]
            artist_names = ", ".join(
                artist["name"] for artist in track.get("artists", [])
            )
            if artist_names:
                track_name += f" by {artist_names}"
            found_track_names.append(track_name)

        # Join track names into one string
        track_names = ", ".join(found_track_names)
        if track_names:
            message = f"Successfully started playback of: {track_names}."
        else:
            message = "No tracks were found to play."

        # If any tracks where missing, append those to the message too
        missing_track_names = []
        for track in result["missing_tracks"]:
            track_name = track["song"]
            if track["artist"]:
                track_name += f" by {track['artist']}"
            missing_track_names.append(track_name)
        if missing_track_names:
            missing_names = ", ".join(missing_track_names)
            message += f" Could not find: {missing_names}."

        return message

    @validate_call
    async def play_album(
        self,
        album_name: str,
        artist_name: str | None = None,
    ) -> str:
        """Play an album.

        Args:
            album_name (str): Name of the album to play.
            artist_name (str | None, optional): Artist of the album if specified by the user. Defaults to None.
        """
        found_album = await asyncio.to_thread(
            self.spotify_client.play_album, self.spotify_id, album_name, artist_name
        )

        if found_album is None:
            requested_album = album_name
            if artist_name:
                requested_album += f" by {artist_name}"
            return f"Could not find album: {requested_album}."

        found_album_name = found_album["name"]
        artist_names = ", ".join(
            artist["name"] for artist in found_album.get("artists", [])
        )
        if artist_names:
            found_album_name += f" by {artist_names}"
        return f"Successfully started playback of album: {found_album_name}."

    @validate_call
    async def play_artist(self, artist_name: str) -> str:
        """Play music by an artist.

        Args:
            artist_name (str): Name of the artist to play.
        """
        found_artist = await asyncio.to_thread(
            self.spotify_client.play_artist,
            self.spotify_id,
            artist_name,
        )

        if found_artist is None:
            return f"Could not find artist: {artist_name}."

        return f"Successfully started playback of music by {found_artist['name']}."

    @validate_call
    async def play_playlist(self, playlist_name: str) -> str:
        """Play a playlist.

        Args:
            playlist_name (str): Name of the playlist to play.
        """
        found_playlist = await asyncio.to_thread(
            self.spotify_client.play_playlist, self.spotify_id, playlist_name
        )

        if found_playlist is None:
            return f"Could not find playlist: {playlist_name}."

        return f"Successfully started playback of playlist: {found_playlist['name']}."

    @validate_call
    async def resume(self) -> str:
        """Resume the currently paused playback."""
        await asyncio.to_thread(
            self.spotify_client.start_playback,
            self.spotify_id,
        )

        return f"Successfully resumed playback on {self.name} speaker."

    @validate_call
    async def pause(self) -> str:
        """Pause the current playback."""
        await asyncio.to_thread(self.spotify_client.pause_playback, self.spotify_id)

        return f"Successfully paused playback of on {self.name} speaker."

    @validate_call
    async def repeat(self, state: Literal["track", "context", "off"]) -> str:
        """Set the repeat mode for playback.

        Args:
            state (Literal["track", "context", "off"]):
                Use "track" to repeat the current track,
                or "context" to repeat the current album or playlist,
                or "off" to disable repeat.
        """
        await asyncio.to_thread(
            self.spotify_client.set_repeat,
            self.spotify_id,
            state,
        )

        return f"Successfully set repeat mode to {state} on {self.name} speaker."

    @validate_call
    async def shuffle(self, state: bool) -> str:
        """Enable or disable shuffle for the current playback.

        Args:
            state (bool): True to enable shuffle, or False to disable it.
        """
        await asyncio.to_thread(
            self.spotify_client.set_shuffle,
            self.spotify_id,
            state,
        )

        return f"Successfully set shuffle mode to {state} on {self.name} speaker."

    @validate_call
    async def add_to_playback_queue(self, tracks_input: list[TrackInput]) -> str:
        """Add one or more tracks to the playback queue.

        Args:
            tracks_input (list[TrackInput]): Tracks to add to queue, including each track name and optional artist.
        """
        tracks = [(track.song, track.artist) for track in tracks_input]
        result = await asyncio.to_thread(
            self.spotify_client.add_to_playback_queue,
            self.spotify_id,
            tracks,
        )

        # Build a list of found track names
        found_track_names = []
        for track in result["found_tracks"]:
            track_name = track["name"]
            artist_names = ", ".join(
                artist["name"] for artist in track.get("artists", [])
            )
            if artist_names:
                track_name += f" by {artist_names}"
            found_track_names.append(track_name)

        # Join track names into one string
        track_names = ", ".join(found_track_names)
        if track_names:
            message = f"Successfully added to the playback queue: {track_names}."
        else:
            message = "No tracks were found to add to the playback queue."

        # If any tracks where missing, append those to the message too
        missing_track_names = []
        for track in result["missing_tracks"]:
            track_name = track["song"]
            if track["artist"]:
                track_name += f" by {track['artist']}"
            missing_track_names.append(track_name)
        if missing_track_names:
            missing_names = ", ".join(missing_track_names)
            message += f" Could not find to add to the playback queue: {missing_names}."

        return message

    @validate_call
    async def navigate_queue(self, direction: Literal["next", "previous"]) -> str:
        """_summary_

        Args:
            direction (Literal["next", "previous"]): Use "next" for the next track or "previous" for the
                previous track.
        """
        if direction == "next":
            await asyncio.to_thread(
                self.spotify_client.play_next_track,
                self.spotify_id,
            )
        elif direction == "previous":
            await asyncio.to_thread(
                self.spotify_client.play_previous_track,
                self.spotify_id,
            )

        return (
            f"Successfully navigated to the {direction} track on {self.name} speaker."
        )

    @validate_call
    async def set_timer(
        self,
        action: Literal["resume", "pause"],
        timer_minutes: Annotated[float, Field(gt=0)] | None = None,
        trigger_time: AwareDatetime | None = None,
    ) -> str:
        """Schedule a future pause or resume action for this speaker.

        Provide either a duration in minutes or an exact timestamp, but not both.

        Args:
            action: Whether to pause or resume the speaker.
            timer_minutes: Duration in minutes, including fractional minutes.
                Convert seconds to minutes by dividing by 60 if request is in seconds.
            trigger_time: Exact future time to run the action, including a timezone.

        Returns:
            The scheduled trigger time in UTC.
        """
        has_duration = timer_minutes is not None
        has_trigger_time = trigger_time is not None

        if has_duration == has_trigger_time:
            raise ValueError("Provide exactly one of timer_minutes or trigger_time")

        if timer_minutes is not None:
            scheduled_time = datetime.now(UTC) + timedelta(minutes=timer_minutes)
        else:
            if trigger_time is None:
                raise ValueError("Provide exactly one of timer_minutes or trigger_time")

            if trigger_time <= datetime.now(UTC):
                raise ValueError("trigger_time must be in the future")

            scheduled_time = trigger_time.astimezone(UTC)

        # Import here to avoid a module cycle between devices, Home, and scheduler.
        from ..scheduler.speakers import save_speaker_timer

        await asyncio.to_thread(
            save_speaker_timer,
            self.db_path,
            self.name,
            action,
            scheduled_time,
        )
        if timer_minutes:
            return f"Successfully set a timer on {self.name} speaker to {action} in {timer_minutes} minutes."
        else:
            return f"Successfully set a timer on {self.name} speaker to {action} at {scheduled_time}."

    @validate_call
    async def cancel_timer(
        self,
        action: Literal["resume", "pause"] | None = None,
        trigger_time: AwareDatetime | None = None,
        cancel_all: bool = False,
    ) -> str:
        """Cancel a single matching timer, or all matching timers on this speaker.

        Omit filters when the user has not specified an action or exact time.
        Unless cancel_all is true, multiple matches require the user to choose
        from the returned options, then call again with the chosen filters.

        Args:
            action: Restrict cancellation to pause or resume timers, if specified.
            trigger_time: Exact scheduled time, including a timezone, if specified.
            cancel_all: Set to true only when the user requests cancellation of all
                matching timers. Supplied filters still apply. Without filters,
                cancels every timer on this speaker. Defaults to false.
        """
        # Import here to avoid a module cycle between devices, Home, and scheduler.
        from ..scheduler.speakers import (
            delete_speaker_timers,
            get_active_timers,
        )

        active_timers = await asyncio.to_thread(
            get_active_timers,
            db_path=self.db_path,
            speaker_name=self.name,
            action=action,
            time=trigger_time,
        )

        if not active_timers:
            return f"No timers match the supplied filters for the {self.name} speaker."

        # If multiple timers match the query and we aren't cancelling all
        if len(active_timers) > 1 and not cancel_all:
            options = []
            for _, _, timer_action, execute_at in active_timers:
                scheduled_time = datetime.fromtimestamp(execute_at, UTC)
                options.append(f"{timer_action} at {scheduled_time.isoformat()}")
            return (
                f"Multiple timers match for the {self.name} speaker: "
                + "; ".join(options)
                + ". No timers were cancelled. Ask the user which timer to cancel."
            )

        # Otherwise delete all timers that are in the active timer list
        timer_ids = [timer[0] for timer in active_timers]
        deleted_count = await asyncio.to_thread(
            delete_speaker_timers, self.db_path, timer_ids
        )
        if cancel_all:
            return f"Cancelled {deleted_count} matching timer(s) on the {self.name} speaker."

        if deleted_count == 0:
            return f"The matching timer on the {self.name} speaker no longer exists. No timers were cancelled."

        # If not cancel all, get info on the returned active timer, and send it up
        _, _, timer_action, execute_at = active_timers[0]
        scheduled_time = datetime.fromtimestamp(execute_at, UTC)
        return (
            f"The {timer_action} timer on the {self.name} speaker set for "
            f"{scheduled_time.isoformat()} has been cancelled."
        )

    @validate_call
    async def get_timers(
        self,
        action: Literal["resume", "pause"] | None = None,
        trigger_time: AwareDatetime | None = None,
    ) -> str:
        """List scheduled timers on this speaker without changing them.

        Omit filters to list every timer on this speaker.

        Args:
            action: Restrict results to pause or resume timers, if specified.
            trigger_time: Exact scheduled time, including a timezone, if specified.

        Returns:
            Matching timer actions and their scheduled times in UTC.
        """
        # Import here to avoid a module cycle between devices, Home, and scheduler.
        from ..scheduler.speakers import get_active_timers

        active_timers = await asyncio.to_thread(
            get_active_timers,
            db_path=self.db_path,
            speaker_name=self.name,
            action=action,
            time=trigger_time,
        )

        if not active_timers:
            return f"No timers match the supplied filters for the {self.name} speaker."

        options = []
        for _, _, timer_action, execute_at in active_timers:
            scheduled_time = datetime.fromtimestamp(execute_at, UTC)
            options.append(f"{timer_action} at {scheduled_time.isoformat()}")
        return f"Timers on the {self.name} speaker: " + "; ".join(options) + "."

    async def get_state(self, snapshot: dict[str, Any] | None = None) -> SpeakerState:
        """Read current playback without storing it on this speaker.

        Home may supply a Spotify response fetched within the same request so
        listing several speakers doesn't repeat the account-wide API calls.
        """

        # We get data from a spotify client snapshot
        if snapshot is None:
            snapshot = await asyncio.to_thread(self.spotify_client.get_status_snapshot)
        device = next(
            (item for item in snapshot["devices"] if item.get("id") == self.spotify_id),
            None,
        )

        # Unpack data from the device snapshot
        is_active = device is not None and device.get("is_active", False)
        playback = (snapshot.get("current_playback") or {}) if is_active else {}
        item = playback.get("item") or {}
        artists = item.get("artists") or []

        # Return speaker state object
        return SpeakerState(
            available=device is not None,
            is_active=is_active,
            is_playing=playback.get("is_playing", False),
            track_uri=item.get("uri"),
            track_name=item.get("name"),
            artist_name=artists[0]["name"] if artists else None,
            volume_percent=device.get("volume_percent") if device else None,
            repeat_state=playback.get("repeat_state"),
            shuffle_state=playback.get("shuffle_state"),
            observed_at=datetime.now(UTC),
        )

    def get_tools(self) -> list[Callable]:
        """Return the speaker operations available to ollama."""
        return [
            self.play_tracks,
            self.play_album,
            self.play_artist,
            self.play_playlist,
            self.pause,
            self.resume,
            self.add_to_playback_queue,
            self.navigate_queue,
            self.set_timer,
            self.cancel_timer,
            self.get_timers,
            self.repeat,
            self.shuffle,
        ]
