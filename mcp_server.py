# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2"]
# ///
"""Agent Composer MCP server: gives Claude tools that act inside the open FL Studio project.

Run by Claude Code over stdio:  uv run --script mcp_server.py
Talks to the in-FL script through the same file bridge as ac.py.

When the Agent Composer app starts Claude it sets AC_APPROVALS=1. Every tool that changes
the project then waits for the person to press Approve or Reject in the app.
Used from plain Claude Code, Claude Code's own permission prompts do that job instead.
"""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ac import send, status  # noqa: E402
import home  # noqa: E402
import midifile  # noqa: E402

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
# Actions that only look. Everything else asks first when approvals are on.
READS = {a for a in ALLOWED if a.split(".")[1].startswith(("get", "is", "ping"))}
READS.add("project.getSnapshot")


def _call(action, params=None):
    r = send(action, params or {})
    r.pop("id", None)
    return r


def _ask(summary, detail=None):
    """Wait for the person's answer in the app. Returns None when approved, else an error dict."""
    if os.environ.get("AC_APPROVALS") != "1" or not home.settings().get("ask_before_changes", True):
        return None
    rid = uuid.uuid4().hex[:10]
    d = home.path("state", "approvals")
    with open(os.path.join(d, rid + ".ask.json"), "w", encoding="utf-8") as f:
        json.dump({"id": rid, "summary": summary, "detail": detail, "at": time.time()}, f)
    answer = os.path.join(d, rid + ".answer.json")
    end = time.time() + 180
    while time.time() < end:
        if os.path.exists(answer):
            with open(answer, encoding="utf-8") as f:
                ok = json.load(f).get("approved")
            for n in (rid + ".ask.json", rid + ".answer.json"):
                try:
                    os.remove(os.path.join(d, n))
                except OSError:
                    pass
            return None if ok else {"success": False, "error": "The person rejected this change. Ask what they'd like instead."}
        time.sleep(0.2)
    try:
        os.remove(os.path.join(d, rid + ".ask.json"))
    except OSError:
        pass
    return {"success": False, "error": "Nobody answered the approval card in 3 minutes, so nothing changed."}


def _change(summary, action, params=None, detail=None):
    no = _ask(summary, detail)
    return no or _call(action, params)


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
    return _change("Set tempo to %g BPM" % bpm, "tempo.set", {"bpm": bpm})


@mcp.tool()
def create_pattern(name: str = "") -> dict:
    """Create a new empty pattern, optionally named, and select it."""
    return _change("Create pattern %s" % (repr(name) if name else "(unnamed)"), "patterns.create", {"name": name})


@mcp.tool()
def rename_pattern(index: int, name: str) -> dict:
    """Rename pattern number `index` (1-based, as FL shows it)."""
    return _change("Rename pattern %d to %r" % (index, name), "patterns.rename", {"index": index, "name": name})


@mcp.tool()
def add_marker(name: str, time: int | None = None) -> dict:
    """Add a playlist marker. `time` in ticks; leave empty for the current song position."""
    p = {"name": name}
    if time is not None:
        p["time"] = time
    return _change("Add marker %r" % name, "arrangement.addMarker", p)


@mcp.tool()
def set_mixer_volume(track: int, volume: float) -> dict:
    """Set a mixer track's fader, 0.0 to 1.0 (0.8 is FL's default 0 dB)."""
    return _change("Mixer %d volume to %d%%" % (track, round(volume * 100)), "mixer.setTrackVolume",
                   {"track": track, "volume": volume})


@mcp.tool()
def mute_mixer_track(track: int, muted: bool | None = None) -> dict:
    """Mute (true), unmute (false) or toggle (empty) a mixer track."""
    word = "Toggle mute on" if muted is None else ("Mute" if muted else "Unmute")
    return _change("%s mixer %d" % (word, track), "mixer.muteTrack", {"track": track, "muted": muted})


@mcp.tool()
def set_step_sequence(channel: int, pattern: list[bool]) -> dict:
    """Write a channel's step-sequencer row in the current pattern, e.g. 16 booleans for one bar of 16ths."""
    grid = "".join("x" if b else "." for b in pattern)
    return _change("Write steps on channel %d" % channel, "channels.setStepSequence",
                   {"channel": channel, "pattern": pattern}, detail=grid)


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
    if os.environ.get("AC_APPROVALS") == "1" and not home.settings().get("allow_save", False):
        return {"success": False, "error": "Saving is switched off in Settings > Safety. Ask the person to save, or to switch it on."}
    return _change("Save the project", "project.save")


# ---- VST dock: look at and tweak the plugins already in the project ----

@mcp.tool()
def list_plugins() -> dict:
    """Every channel with the instrument plugin loaded on it, plus the plugins the person parked in the dock."""
    chans = _call("channels.getAll")
    out = []
    for c in chans.get("channels", []):
        name = _call("plugins.getName", {"index": c["index"]})
        out.append({"channel": c["index"], "channel_name": c["name"], "plugin": name.get("name") or name.get("plugin_name"),
                    "mixer_track": c.get("target_fx_track")})
    return {"channels": out, "parked": home.dock()}


@mcp.tool()
def get_plugin_params(channel: int, max_params: int = 40) -> dict:
    """Named parameters (index, name, value 0..1) of the plugin on a channel."""
    return _call("plugins.getParams", {"index": channel, "max_params": max_params})


@mcp.tool()
def set_plugin_param(channel: int, param_index: int, value: float) -> dict:
    """Set one plugin parameter on a channel, value 0.0 to 1.0."""
    return _change("Set param %d on channel %d to %.2f" % (param_index, channel, value), "plugins.setParamValue",
                   {"plugin_index": channel, "param_index": param_index, "value": value})


@mcp.tool()
def change_preset(channel: int, direction: str = "next") -> dict:
    """Step the plugin on a channel to its next or previous preset (direction 'next' or 'prev')."""
    action = "plugins.prevPreset" if direction == "prev" else "plugins.nextPreset"
    return _change("%s preset on channel %d" % ("Previous" if direction == "prev" else "Next", channel), action,
                   {"index": channel})


@mcp.tool()
def park_plugin(name: str, note: str = "") -> dict:
    """Park a plugin in the person's VST dock so it's one tap away next time (a favourites shelf)."""
    return {"parked": home.park(name, note)}


# ---- Piano roll writer ----

@mcp.tool()
def write_notes(name: str, notes: list[dict], tempo_bpm: float = 0) -> dict:
    """Write a melody, chords or bassline as notes.

    notes: [{"pitch": 60, "start": 0, "length": 1, "velocity": 0.8}], pitch is MIDI (60 = middle C),
    start and length are in beats (1 = a quarter note), velocity 0..1.
    Saves a .mid file in the MIDI folder (drag it into FL) and queues the notes for the
    'Agent Composer' piano roll script (Piano roll > Tools > Scripting > Agent Composer).
    """
    if not notes:
        return {"success": False, "error": "No notes given."}
    no = _ask("Write %d notes as %r" % (len(notes), name), detail=midifile.describe(notes))
    if no:
        return no
    bpm = tempo_bpm or (_call("project.getSnapshot").get("tempo_bpm") or 120)
    path = midifile.write(home.path("MIDI"), name, notes, bpm)
    with open(os.path.join(home.bridge_dir(), "notes.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "notes": notes, "at": time.time()}, f)
    return {"success": True, "midi_file": path,
            "next": "Open the piano roll on a channel, then Tools > Scripting > Agent Composer. Or drag the .mid file in."}


# ---- Voice takes folder ----

@mcp.tool()
def list_takes() -> dict:
    """Audio takes in the person's Takes folder (newest first), with size and age."""
    return {"folder": home.path("Takes"), "takes": home.takes()}


@mcp.tool()
def rename_take(old_name: str, new_name: str) -> dict:
    """Rename a take in the Takes folder (keeps the file extension)."""
    no = _ask("Rename take %r to %r" % (old_name, new_name))
    return no or home.rename_take(old_name, new_name)


@mcp.tool()
def run_action(action: str, params: dict | None = None) -> dict:
    """Any other Agent Composer action by exact name (mixer.*, channels.*, plugins.*, transport.*).
    See ALLOWED in mcp_server.py for the list."""
    if action not in ALLOWED:
        return {"success": False, "error": "Unknown action %r. Allowed: %s" % (action, ", ".join(sorted(ALLOWED)))}
    if action in READS:
        return _call(action, params)
    return _change("Run %s" % action, action, params, detail=json.dumps(params or {}))


if __name__ == "__main__":
    mcp.run()
