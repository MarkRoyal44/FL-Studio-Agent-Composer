# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2"]
# ///
"""Agent Composer MCP server (L1): gives Claude tools that act inside the open FL Studio project.

Run by Claude Code over stdio:  uv run --script mcp_server.py
Talks to the in-FL script through the same file bridge as ac.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ac import send, status  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("agent-composer")

# Every action the in-FL script accepts. run_action refuses anything else.
ALLOWED = {
    "bridge.ping", "project.getSnapshot", "project.save", "general.undo", "tempo.set",
    "patterns.create", "patterns.rename", "patterns.select", "arrangement.addMarker",
    "transport.start", "transport.stop", "transport.record", "transport.getStatus", "transport.setPosition",
    "transport.getLength", "transport.setLoopMode", "transport.setPlaybackSpeed",
    "mixer.getAllTracks", "mixer.getTrackCount", "mixer.getTrackInfo", "mixer.setTrackVolume", "mixer.setTrackPan",
    "mixer.muteTrack", "mixer.soloTrack", "mixer.armTrack", "mixer.setTrackName", "mixer.setTrackColor",
    "mixer.setStereoSep",
    "channels.getAll", "channels.getCount", "channels.getInfo", "channels.getSelected", "channels.select",
    "channels.selectOne", "channels.setName", "channels.setColor", "channels.setVolume", "channels.setPan",
    "channels.mute", "channels.solo", "channels.routeToMixer", "channels.triggerNote",
    "channels.getGridBit", "channels.setGridBit", "channels.getStepSequence", "channels.setStepSequence",
    "plugins.isValid", "plugins.getName", "plugins.getColor", "plugins.getParamCount", "plugins.getParams",
    "plugins.getParamValue", "plugins.setParamValue", "plugins.getPresetCount", "plugins.nextPreset",
    "plugins.prevPreset",
}


def _call(action, params=None):
    r = send(action, params or {})
    r.pop("id", None)
    return r


@mcp.tool()
def bridge_status() -> dict:
    """Is the Agent Composer script alive inside FL Studio? Returns heartbeat age and FL's Python info."""
    return status()


@mcp.tool()
def get_project_snapshot() -> dict:
    """The whole open project in one read: tempo, transport, channels, patterns, named mixer and playlist tracks.
    Call this first every turn before changing anything."""
    return _call("project.getSnapshot")


@mcp.tool()
def set_tempo(bpm: float) -> dict:
    """Set the project tempo in BPM (experimental FL API, read the snapshot after to confirm)."""
    return _call("tempo.set", {"bpm": bpm})


@mcp.tool()
def create_pattern(name: str = "") -> dict:
    """Create a new empty pattern, optionally named, and select it."""
    return _call("patterns.create", {"name": name})


@mcp.tool()
def rename_pattern(index: int, name: str) -> dict:
    """Rename pattern number `index` (1-based, as FL shows it)."""
    return _call("patterns.rename", {"index": index, "name": name})


@mcp.tool()
def add_marker(name: str, time: int | None = None) -> dict:
    """Add a playlist marker. `time` in ticks; leave empty for the current song position."""
    p = {"name": name}
    if time is not None:
        p["time"] = time
    return _call("arrangement.addMarker", p)


@mcp.tool()
def set_mixer_volume(track: int, volume: float) -> dict:
    """Set a mixer track's fader, 0.0 to 1.0 (0.8 is FL's default 0 dB)."""
    return _call("mixer.setTrackVolume", {"track": track, "volume": volume})


@mcp.tool()
def mute_mixer_track(track: int, muted: bool | None = None) -> dict:
    """Mute (true), unmute (false) or toggle (empty) a mixer track."""
    return _call("mixer.muteTrack", {"track": track, "muted": muted})


@mcp.tool()
def set_step_sequence(channel: int, pattern: list[bool]) -> dict:
    """Write a channel's step-sequencer row in the current pattern, e.g. 16 booleans for one bar of 16ths."""
    return _call("channels.setStepSequence", {"channel": channel, "pattern": pattern})


@mcp.tool()
def play() -> dict:
    """Start playback."""
    return _call("transport.start")


@mcp.tool()
def stop() -> dict:
    """Stop playback."""
    return _call("transport.stop")


@mcp.tool()
def undo() -> dict:
    """Undo the last change (each Agent Composer change is one undo step)."""
    return _call("general.undo")


@mcp.tool()
def save_project() -> dict:
    """Save the project to its current file."""
    return _call("project.save")


@mcp.tool()
def run_action(action: str, params: dict | None = None) -> dict:
    """Any other Agent Composer action by exact name (mixer.*, channels.*, plugins.*, transport.*).
    See ALLOWED in mcp_server.py for the list."""
    if action not in ALLOWED:
        return {"success": False, "error": "Unknown action %r. Allowed: %s" % (action, ", ".join(sorted(ALLOWED)))}
    return _call(action, params)


if __name__ == "__main__":
    mcp.run()
