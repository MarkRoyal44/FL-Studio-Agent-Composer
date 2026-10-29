"""Agent Composer bridge CLI: talk to the script running inside FL Studio.

  py ac.py status                      is the script alive, and what imports inside FL
  py ac.py ping
  py ac.py snapshot
  py ac.py send <action> ['{"json": "params"}']
"""
import json
import os
import sys
import time
import uuid

BRIDGE = os.path.join(os.environ["USERPROFILE"], "Documents", "Image-Line", "FL Studio", "Settings", "Hardware", "AgentComposer", "bridge")
COMMAND, RESPONSE, STATUS = (os.path.join(BRIDGE, n) for n in ("command.json", "response.json", "status.json"))


def send(action, params=None, timeout=5.0):
    os.makedirs(BRIDGE, exist_ok=True)
    cid = uuid.uuid4().hex[:12]
    tmp = COMMAND + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"id": cid, "action": action, "params": params or {}}, f)
    os.replace(tmp, COMMAND)
    end = time.time() + timeout
    while time.time() < end:
        try:
            with open(RESPONSE, encoding="utf-8") as f:
                r = json.load(f)
            if r.get("id") == cid:
                return r
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    try:
        os.remove(COMMAND)
    except OSError:
        pass
    return {"id": cid, "success": False, "error": "FL didn't answer in %.0fs. Is FL open with Agent Composer picked in MIDI settings?" % timeout}


def status():
    try:
        with open(STATUS, encoding="utf-8") as f:
            s = json.load(f)
        s["seconds_since_heartbeat"] = round(time.time() - os.path.getmtime(STATUS), 1)
        return s
    except OSError:
        return {"alive": False, "error": "No heartbeat yet: the script has never loaded in FL."}


if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    if a[0] == "status":
        out = status()
    elif a[0] == "ping":
        out = send("bridge.ping")
    elif a[0] == "snapshot":
        out = send("project.getSnapshot")
    elif a[0] == "send" and len(a) >= 2:
        out = send(a[1], json.loads(a[2]) if len(a) > 2 else {})
    else:
        print(__doc__)
        sys.exit(2)
    print(json.dumps(out, indent=2))
