"""Agent Composer app: a small local server that shows the chat window and runs Claude Code for it.

  python app/server.py            start and open the window
  python app/server.py --no-open  start only (then visit the printed address)

Standard library only. Claude Code does the thinking; the agent-composer MCP server
(mcp_server.py) is the only set of tools it gets, so it can touch FL and nothing else.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import home  # noqa: E402
from ac import send, status  # noqa: E402

VERSION = "0.2.0"
UI = os.path.join(ROOT, "app", "ui")
PORT = int(os.environ.get("AGENT_COMPOSER_PORT", "47800"))
TOOL_PREFIX = "mcp__agent-composer__"

PERSONA = """You are Agent Composer, a music-production assistant living inside the person's FL Studio.
You act on the open project only through your agent-composer tools.
- Call get_project_snapshot before changing anything, and after, to confirm.
- Keep replies short, warm and plain. Talk like a producer in the room, not a manual.
- Each change is one undo step; offer `undo` when something lands wrong.
- Notes for melodies, chords and basslines go through write_notes (beats: 1 = a quarter note).
- The VST dock is list_plugins / get_plugin_params / set_plugin_param / change_preset / park_plugin.
  You can't load a new plugin into FL; say so and suggest parking it instead.
- If a tool says the person rejected a change, accept it and ask what they want instead.
- If FL isn't answering, tell them to open FL and pick Agent Composer in MIDI settings."""

_run = {"proc": None}
_lock = threading.Lock()


def claude_path():
    return shutil.which("claude")


def mcp_config():
    p = os.path.join(home.path("state"), "mcp.json")
    uv = shutil.which("uv") or "uv"
    cfg = {"mcpServers": {"agent-composer": {
        "command": uv, "args": ["run", "--quiet", "--script", os.path.join(ROOT, "mcp_server.py")],
        "env": {"AC_APPROVALS": "1", "AGENT_COMPOSER_HOME": home.HOME}}}}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return p


def remember_session(sid, title):
    s = home._read("sessions.json", [])
    s = [x for x in s if x["id"] != sid]
    old = next((x for x in home._read("sessions.json", []) if x["id"] == sid), None)
    s.insert(0, {"id": sid, "title": (old or {}).get("title") or title[:60], "at": time.time()})
    home._write("sessions.json", s[:50])


def chat(text, session_id, emit):
    """Run one turn through Claude Code and emit small events as they arrive."""
    exe = claude_path()
    if not exe:
        emit({"type": "error", "text": "Claude Code isn't installed or isn't on PATH. See the README, step 1."})
        return
    st = home.settings()
    args = [exe, "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--mcp-config", mcp_config(), "--strict-mcp-config", "--tools", "",
            "--allowedTools", "mcp__agent-composer", "--permission-mode", "dontAsk",
            "--setting-sources", "project", "--append-system-prompt", PERSONA, "--model", st.get("model") or "opus"]
    if session_id:
        args += ["--resume", session_id]
    env = dict(os.environ)
    if st.get("brain") == "claude-api":
        if not env.get("ANTHROPIC_API_KEY"):
            emit({"type": "error", "text": "The Claude API brain needs ANTHROPIC_API_KEY set on this computer. Switch to Claude Code in Settings, or set the key and restart."})
            emit({"type": "done", "session_id": session_id})
            return
    else:
        env.pop("ANTHROPIC_API_KEY", None)  # Claude Code brain runs on the person's plan, never a stray key
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    errlog = open(os.path.join(home.path("state"), "claude-stderr.log"), "w+b")
    proc = subprocess.Popen(args, cwd=home.path("state"), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=errlog, env=env, creationflags=flags)
    with _lock:
        _run["proc"] = proc
    proc.stdin.write(text.encode("utf-8"))
    proc.stdin.close()
    streamed, sid = False, session_id
    for raw in proc.stdout:
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            sid = ev.get("session_id") or sid
            emit({"type": "session", "id": sid})
        elif t == "stream_event":
            e = ev.get("event", {})
            d = e.get("delta", {})
            if e.get("type") == "content_block_delta" and d.get("type") == "text_delta":
                streamed = True
                emit({"type": "text", "delta": d.get("text", "")})
            elif e.get("type") == "message_start":
                streamed = False
        elif t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    emit({"type": "tool", "id": b["id"], "name": b["name"].replace(TOOL_PREFIX, ""), "input": b.get("input")})
                elif b.get("type") == "text" and not streamed:
                    emit({"type": "text", "delta": b.get("text", "")})
        elif t == "user":
            content = ev.get("message", {}).get("content", [])
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result":
                    body = b.get("content")
                    if isinstance(body, list):
                        body = " ".join(x.get("text", "") for x in body if isinstance(x, dict))
                    body = str(body or "")
                    ok = not b.get("is_error") and '"success": false' not in body.replace("'", '"').lower()
                    emit({"type": "tool_done", "id": b.get("tool_use_id"), "ok": ok, "summary": body[:400]})
        elif t == "result":
            sid = ev.get("session_id") or sid
            if ev.get("is_error"):
                emit({"type": "error", "text": str(ev.get("result") or ev.get("subtype"))[:400]})
    proc.wait()
    with _lock:
        _run["proc"] = None
    if proc.returncode not in (0, None) and proc.returncode != 1:
        errlog.seek(0)
        err = errlog.read().decode("utf-8", "replace")[-400:]
        if err.strip():
            emit({"type": "error", "text": err})
    errlog.close()
    if sid:
        remember_session(sid, text)
    emit({"type": "done", "session_id": sid})


def stop_chat():
    with _lock:
        p = _run["proc"]
    if p and p.poll() is None:
        if os.name == "nt":
            subprocess.call(["taskkill", "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            p.kill()
        return True
    return False


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
            return self._json({"ok": True, "version": VERSION, "fl": status(), "claude": bool(claude_path()),
                               "uv": bool(shutil.which("uv")), "home": home.HOME})
        if p == "/api/snapshot":
            return self._json(fl("project.getSnapshot"))
        if p == "/api/settings":
            return self._json(home.settings())
        if p == "/api/approvals":
            return self._json(approvals())
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
        if p == "/api/stop":
            return self._json({"stopped": stop_chat()})
        if p == "/api/settings":
            return self._json(home.save_settings(b))
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
            which = {"takes": "Takes", "midi": "MIDI"}.get(b.get("which"), "")
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
            return
    webbrowser.open(url)


def main():
    port = PORT
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
