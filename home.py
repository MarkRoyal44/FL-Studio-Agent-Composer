"""Where Agent Composer keeps the person's things: settings, the VST dock, MIDI files, voice takes and the Mini Brain.

Default home is Documents/Agent Composer. Set AGENT_COMPOSER_HOME to move it.
"""
import json
import os
import time

HOME = os.environ.get("AGENT_COMPOSER_HOME") or os.path.join(os.path.expanduser("~"), "Documents", "Agent Composer")
AUDIO = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aif", ".aiff")

DEFAULTS = {
    "ask_before_changes": True,
    "dock_to_fl": True,
    "allow_save": False,
    "model": "opus",
    "brain": "claude-code",
    "brain_models": {},
    "mini_brain": True,
    "read_aloud": False,
    "sounds": True,
    "voice_server": "",
}


def path(*parts):
    p = os.path.join(HOME, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def bridge_dir():
    # Same folder ac.py and the in-FL script use.
    from ac import BRIDGE
    os.makedirs(BRIDGE, exist_ok=True)
    return BRIDGE


def _read(name, default):
    try:
        with open(os.path.join(path("state"), name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(name, data):
    p = os.path.join(path("state"), name)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(p + ".tmp", p)


def settings():
    return {**DEFAULTS, **_read("settings.json", {})}


def save_settings(changes):
    s = settings()
    s.update({k: v for k, v in changes.items() if k in DEFAULTS})
    _write("settings.json", s)
    return s


def dock():
    return _read("dock.json", [])


def park(name, note=""):
    d = [p for p in dock() if p["name"].lower() != name.lower()]
    d.insert(0, {"name": name, "note": note, "at": time.time()})
    _write("dock.json", d)
    return d


def unpark(name):
    d = [p for p in dock() if p["name"].lower() != name.lower()]
    _write("dock.json", d)
    return d


def takes():
    folder = path("Takes")
    out = []
    for n in os.listdir(folder):
        p = os.path.join(folder, n)
        if os.path.isfile(p) and n.lower().endswith(AUDIO):
            st = os.stat(p)
            out.append({"name": n, "kb": round(st.st_size / 1024), "modified": st.st_mtime})
    return sorted(out, key=lambda t: -t["modified"])


def rename_take(old, new):
    folder = path("Takes")
    old = os.path.basename(old)
    src = os.path.join(folder, old)
    if not os.path.isfile(src):
        return {"success": False, "error": "No take called %r." % old}
    ext = os.path.splitext(old)[1]
    new = os.path.basename(new)
    if not new.lower().endswith(ext.lower()):
        new += ext
    dst = os.path.join(folder, new)
    if os.path.exists(dst):
        return {"success": False, "error": "%r already exists." % new}
    os.rename(src, dst)
    return {"success": True, "name": new}
