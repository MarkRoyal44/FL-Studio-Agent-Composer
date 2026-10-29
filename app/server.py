"""Agent Composer app: a small local server that shows the chat window and runs Claude Code for it.

  python app/server.py            start and open the window
  python app/server.py --no-open  start only (then visit the printed address)

Standard library only. A brain (Claude Code, Codex, OpenCode, DeepSeek, a local model or your own,
see brains.py) does the thinking; the agent-composer MCP server (mcp_server.py) is the only set of
tools it gets, so it can touch FL and nothing else.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "app"))
import home  # noqa: E402
import brains  # noqa: E402
import minibrain  # noqa: E402
from ac import send, status  # noqa: E402

VERSION = "0.7.0"
UI = os.path.join(ROOT, "app", "ui")
PORT = int(os.environ.get("AGENT_COMPOSER_PORT", "47800"))

def claude_path():
    return shutil.which("claude")


def chat(text, session_id, emit):
    """Run one turn on the plugged-in brain (see brains.py) and stream its events."""
    sid = brains.run(text, session_id, emit)
    emit({"type": "done", "session_id": sid})


def stop_chat():
    return brains.stop()


def approvals():
    d = home.path("state", "approvals")
    out = []
    for n in sorted(os.listdir(d)):
        if n.endswith(".ask.json"):
            try:
                with open(os.path.join(d, n), encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, ValueError):
                pass
    return out


def answer(rid, ok):
    rid = "".join(c for c in rid if c.isalnum())
    with open(os.path.join(home.path("state", "approvals"), rid + ".answer.json"), "w", encoding="utf-8") as f:
        json.dump({"approved": bool(ok)}, f)
    return {"ok": True}


def fl(action, params=None, timeout=4.0):
    r = send(action, params or {}, timeout=timeout)
    r.pop("id", None)
    return r


def dock():
    chans = fl("channels.getAll").get("channels", [])
    out = []
    for c in chans:
        n = fl("plugins.getName", {"index": c["index"]})
        out.append({"channel": c["index"], "channel_name": c["name"], "plugin": n.get("name"),
                    "muted": c.get("is_muted"), "selected": c.get("is_selected")})
    return {"channels": out, "parked": home.dock()}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *a):
        pass

    def _json(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, p, ctype):
        try:
            with open(p, "rb") as f:
                body = f.read()
        except OSError:
            return self._json({"error": "not found"}, 404)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path
        if p in ("/", "/index.html"):
            return self._file(os.path.join(UI, "index.html"), "text/html; charset=utf-8")
        if p == "/api/health":
            b = brains.get(home.settings().get("brain"))
            return self._json({"ok": True, "version": VERSION, "fl": status(), "claude": bool(claude_path()),
                               "brain": b["name"], "brain_ready": brains.check(b)[0],
                               "uv": bool(shutil.which("uv")), "home": home.HOME})
        if p == "/api/snapshot":
            return self._json(fl("project.getSnapshot"))
        if p == "/api/settings":
            return self._json(home.settings())
        if p == "/api/approvals":
            return self._json(approvals())
        if p == "/api/brains":
            return self._json({"brains": [brains.public(x) for x in brains.all_brains()],
                               "plugged": home.settings().get("brain"), "kinds": list(brains.KINDS)})
        if p == "/api/minibrain":
            return self._json({"folder": minibrain.folder(), "on": minibrain.on(), "documents": minibrain.docs()})
        if p == "/api/sessions":
            return self._json(home._read("sessions.json", []))
        if p == "/api/dock":
            return self._json(dock())
        if p == "/api/params":
            return self._json(fl("plugins.getParams", {"index": int(q.get("channel", ["0"])[0]), "max_params": 40}))
        if p == "/api/takes":
            return self._json({"folder": home.path("Takes"), "takes": home.takes()})
        if p == "/api/midi":
            d = home.path("MIDI")
            files = sorted(((n, os.path.getmtime(os.path.join(d, n))) for n in os.listdir(d) if n.endswith(".mid")), key=lambda x: -x[1])
            return self._json({"folder": d, "files": [{"name": n, "modified": m} for n, m in files]})
        if p.startswith("/takes/"):
            name = os.path.basename(unquote(p[len("/takes/"):]))
            ext = os.path.splitext(name)[1].lower()
            ctype = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".flac": "audio/flac", ".m4a": "audio/mp4"}.get(ext, "application/octet-stream")
            return self._file(os.path.join(home.path("Takes"), name), ctype)
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        # A custom header makes browsers preflight cross-site requests, which this server never answers.
        if self.headers.get("X-Agent-Composer") != "1":
            return self._json({"error": "missing header"}, 403)
        p = urlparse(self.path).path
        b = self._body()
        if p == "/api/chat":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            def emit(ev):
                try:
                    self.wfile.write((json.dumps(ev) + "\n").encode("utf-8"))
                    self.wfile.flush()
                except OSError:
                    stop_chat()
            try:
                chat(str(b.get("text", "")), b.get("session_id"), emit)
            except Exception as e:  # keep the window alive and say what broke
                emit({"type": "error", "text": "Agent Composer hit an error: %r" % (e,)})
                emit({"type": "done"})
            return
        if p == "/api/brains":
            return self._json(brains.add_custom(b.get("brain")))
        if p == "/api/brains/remove":
            return self._json(brains.remove_custom(str(b.get("id", ""))))
        if p == "/api/brains/key":
            return self._json(brains.set_key(str(b.get("id", "")), str(b.get("key", ""))))
        if p == "/api/minibrain/add":
            return self._json(minibrain.add(b.get("name"), b.get("data")))
        if p == "/api/minibrain/remove":
            return self._json(minibrain.remove(b.get("name")))
        if p == "/api/stop":
            return self._json({"stopped": stop_chat()})
        if p == "/api/settings":
            r = home.save_settings(b)
            if "dock_to_fl" in b:
                dock_window(bool(b["dock_to_fl"]))
            return self._json(r)
        if p == "/api/dock-window":
            return self._json(dock_window(bool(b.get("on", True))))
        if p.startswith("/api/approvals/"):
            return self._json(answer(p.rsplit("/", 1)[1], b.get("approved")))
        if p == "/api/park":
            return self._json(home.park(str(b.get("name", "")), str(b.get("note", ""))))
        if p == "/api/unpark":
            return self._json(home.unpark(str(b.get("name", ""))))
        if p == "/api/preset":
            a = "plugins.prevPreset" if b.get("direction") == "prev" else "plugins.nextPreset"
            return self._json(fl(a, {"index": int(b.get("channel", 0))}))
        if p == "/api/param":
            return self._json(fl("plugins.setParamValue", {"plugin_index": int(b.get("channel", 0)),
                                                         "param_index": int(b.get("param", 0)), "value": float(b.get("value", 0))}))
        if p == "/api/transport":
            return self._json(fl("transport.start" if b.get("play") else "transport.stop"))
        if p == "/api/undo":
            return self._json(fl("general.undo"))
        if p == "/api/rename-take":
            return self._json(home.rename_take(str(b.get("old", "")), str(b.get("new", ""))))
        if p == "/api/open-folder":
            which = {"takes": "Takes", "midi": "MIDI", "minibrain": "Mini Brain"}.get(b.get("which"), "")
            target = home.path(which) if which else home.HOME
            if os.name == "nt":
                os.startfile(target)  # noqa: S606 - opens the person's own folder in Explorer
            return self._json({"opened": target})
        return self._json({"error": "not found"}, 404)


def open_window(url):
    edge = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    chrome = [os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
              os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")]
    for exe in edge + chrome:
        if os.path.isfile(exe):
            subprocess.Popen([exe, "--app=" + url, "--window-size=460,820"])
            if os.name == "nt" and home.settings().get("dock_to_fl", True):
                threading.Thread(target=auto_dock, daemon=True).start()
            return
    webbrowser.open(url)


# Dock: make the app window an "owned" window of FL's main window, the same way FL's own
# plugin windows work. It then floats over FL, minimizes with FL and sits inside its frame.
def _win_find(cls=None, title=None):
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    hit = []
    proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _):
        if not u.IsWindowVisible(h):
            return True
        t, c = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(h, t, 256)
        u.GetClassNameW(h, c, 256)
        if (cls is None or c.value == cls) and (title is None or t.value == title):
            hit.append(h)
        return True
    u.EnumWindows(proto(cb), 0)
    return hit[0] if hit else None


def dock_window(on=True):
    """Pin the Agent Composer window inside FL (on) or let it float free (off)."""
    if os.name != "nt":
        return {"docked": False, "error": "Docking works on Windows only."}
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    u.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    me = _win_find("Chrome_WidgetWin_1", "Agent Composer")
    if not me:
        return {"docked": False, "error": "The Agent Composer window isn't open."}
    flw = _win_find("TFruityLoopsMainForm") if on else None
    if on and not flw:
        return {"docked": False, "error": "FL Studio isn't open."}
    u.SetWindowLongPtrW(me, -8, flw)  # GWLP_HWNDPARENT: the owner
    if flw:
        fr, mr = wintypes.RECT(), wintypes.RECT()
        u.GetWindowRect(flw, ctypes.byref(fr))
        u.GetWindowRect(me, ctypes.byref(mr))
        w, h = mr.right - mr.left, mr.bottom - mr.top
        h = min(h, fr.bottom - fr.top - 120)
        u.SetWindowPos(me, 0, fr.right - w - 12, fr.top + 96, w, h, 0x0014)  # NOZORDER|NOACTIVATE
    return {"docked": bool(flw)}


def auto_dock():
    # The window takes a moment to open; FL may open later still.
    import time
    for _ in range(60):
        time.sleep(1)
        if not home.settings().get("dock_to_fl", True):
            return
        if dock_window(True).get("docked"):
            return


def fl_favorite():
    """Put the Agent Composer plugin at the top of FL's Add menu.

    FL lists favorites from Plugin database/Generators. Once FL has scanned the plugin it writes
    an entry under Installed/; copying that entry up makes it a favorite, like starring it in FL's
    Plugin Manager.
    """
    db = os.path.join(os.path.expanduser("~"), "Documents", "Image-Line", "FL Studio", "Presets", "Plugin database")
    fav = os.path.join(db, "Generators", "Agent Composer.fst")
    if os.path.isfile(fav):
        return True
    for root, _, files in os.walk(os.path.join(db, "Installed", "Generators")):
        if "Agent Composer.fst" in files:
            for ext in (".fst", ".nfo"):
                src = os.path.join(root, "Agent Composer" + ext)
                if os.path.isfile(src):
                    shutil.copyfile(src, os.path.join(db, "Generators", "Agent Composer" + ext))
            return True
    return False

def watch_favorite():
    # FL may scan the plugin while the app is already running, so keep checking until it lands.
    import time
    while True:
        try:
            if fl_favorite():
                return
        except OSError:
            pass
        time.sleep(30)


def already_running():
    # Windows lets a second server bind the same port, so ask first instead of starting twice.
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/health" % PORT, timeout=1) as r:
            return json.load(r).get("ok") is True
    except Exception:
        return False


def main():
    port = PORT
    threading.Thread(target=watch_favorite, daemon=True).start()
    if already_running():
        print("Agent Composer is already running at http://127.0.0.1:%d/" % PORT)
        if "--no-open" not in sys.argv:
            open_window("http://127.0.0.1:%d/" % PORT)
            if home.settings().get("dock_to_fl", True):
                auto_dock()  # this process exits next, so dock here rather than on a thread
        return
    for _ in range(20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            port += 1
    else:
        sys.exit("No free port near %d." % PORT)
    url = "http://127.0.0.1:%d/" % port
    print("Agent Composer %s running at %s  (Ctrl+C to quit)" % (VERSION, url))
    if "--no-open" not in sys.argv:
        threading.Timer(0.4, open_window, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
