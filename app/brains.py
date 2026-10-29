"""Brains: the swappable thinking part of Agent Composer.

Every brain gets the same agent-composer MCP tools and nothing else, and streams the same small
events to the window: session, text, tool, tool_done, error, done.

Kinds
  claude    Claude Code headless (claude -p, stream-json)
  codex     Codex CLI (codex exec --json), shell and apps switched off
  opencode  OpenCode (opencode run --format json), built-in tools switched off
  openai    any OpenAI-compatible chat API (DeepSeek, Ollama, OpenRouter, LM Studio...).
            Agent Composer runs the tool loop itself and talks to the MCP server directly.
  cli       your own harness: a command that gets the prompt and an MCP config path,
            and prints text (or claude / codex / opencode JSON, see "format")

Custom brains live in Documents/Agent Composer/state/brains.json. Keys live in state/keys.json.
Neither is ever inside the repo.
"""
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid

import home

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = "agent-composer"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

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

BUILTIN = [
    {"id": "claude-code", "kind": "claude", "name": "Claude Code", "sub": "Your Claude plan. Opus, Sonnet or Haiku.", "builtin": True},
    {"id": "claude-api", "kind": "claude", "name": "Claude API", "sub": "Pay as you go with your Anthropic key.",
     "api_key_env": "ANTHROPIC_API_KEY", "builtin": True},
    {"id": "codex", "kind": "codex", "name": "Codex", "sub": "Your ChatGPT plan, through the Codex CLI.", "model": "", "builtin": True},
    {"id": "opencode", "kind": "opencode", "name": "OpenCode", "sub": "Any provider you've set up in OpenCode.",
     "model": "", "builtin": True},
    {"id": "deepseek", "kind": "openai", "name": "DeepSeek", "sub": "DeepSeek's API with your key. Cheap and quick.",
     "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat", "api_key_env": "DEEPSEEK_API_KEY", "builtin": True},
    {"id": "ollama", "kind": "openai", "name": "Local (Ollama)", "sub": "Free and offline. Pick a model that supports tools.",
     "base_url": "http://localhost:11434/v1", "model": "qwen3:8b", "builtin": True},
]
KINDS = ("claude", "codex", "opencode", "openai", "cli")
FORMATS = ("text", "claude", "codex", "opencode")

_run = {"proc": None, "cancel": threading.Event()}
_lock = threading.Lock()


# ---------- registry ----------

def _keys():
    return home._read("keys.json", {})


def custom():
    return home._read("brains.json", [])


def all_brains():
    over = home.settings().get("brain_models") or {}
    out = []
    for b in BUILTIN + custom():
        b = dict(b)
        if b["id"] in over and over[b["id"]]:
            b["model"] = over[b["id"]]
        out.append(b)
    return out


def get(bid):
    return next((b for b in all_brains() if b["id"] == bid), None) or BUILTIN[0]


def api_key(b):
    if b.get("api_key"):
        return b["api_key"]
    env = b.get("api_key_env")
    return (os.environ.get(env) if env else None) or _keys().get(b["id"]) or ""


def check(b):
    """Return (ready, why) without running anything."""
    k = b["kind"]
    if k == "claude":
        if not shutil.which("claude"):
            return False, "Install Claude Code and run `claude` once to sign in."
        if b.get("api_key_env") and not api_key(b):
            return False, "Add your Anthropic key below, or set ANTHROPIC_API_KEY."
    elif k == "codex" and not shutil.which("codex"):
        return False, "Install the Codex CLI and run `codex login` once."
    elif k == "opencode" and not shutil.which("opencode"):
        return False, "Install OpenCode and run `opencode auth login` once."
    elif k == "openai":
        local = "localhost" in b.get("base_url", "") or "127.0.0.1" in b.get("base_url", "")
        if not local and not api_key(b):
            return False, "Add your key below%s." % (", or set " + b["api_key_env"] if b.get("api_key_env") else "")
    elif k == "cli":
        cmd = b.get("command") or []
        if not cmd or not shutil.which(cmd[0]):
            return False, "Command %r isn't on PATH." % (cmd[0] if cmd else "")
    if shutil.which("uv") is None:
        return False, "Install uv; it runs the FL tools."
    return True, ""


def public(b):
    """What the window may see: no keys, ever."""
    ready, why = check(b)
    out = {k: v for k, v in b.items() if k not in ("api_key",)}
    out["has_key"] = bool(api_key(b))
    out["ready"], out["why"] = ready, why
    return out


def validate(b):
    if not isinstance(b, dict):
        return "Paste one JSON object."
    if not str(b.get("name", "")).strip():
        return 'Give it a "name".'
    if b.get("kind") not in KINDS:
        return '"kind" must be one of: %s.' % ", ".join(KINDS)
    if b["kind"] == "openai" and not str(b.get("base_url", "")).startswith(("http://", "https://")):
        return 'An openai brain needs "base_url", like https://api.deepseek.com/v1.'
    if b["kind"] == "openai" and not b.get("model"):
        return 'An openai brain needs "model".'
    if b["kind"] == "cli":
        if not isinstance(b.get("command"), list) or not b["command"]:
            return 'A cli brain needs "command" as a list, like ["myagent", "{prompt}"].'
        if b.get("format", "text") not in FORMATS:
            return '"format" must be one of: %s.' % ", ".join(FORMATS)
    return ""


def add_custom(b):
    err = validate(b)
    if err:
        return {"success": False, "error": err}
    b = {k: v for k, v in b.items() if k != "builtin"}
    base = "".join(c if c.isalnum() else "-" for c in b["name"].lower()).strip("-") or "brain"
    b["id"] = b.get("id") if str(b.get("id", "")).startswith("custom-") else "custom-" + base
    if b.get("api_key"):  # keep keys out of brains.json so it can be shared safely
        k = _keys()
        k[b["id"]] = b.pop("api_key")
        home._write("keys.json", k)
    lst = [x for x in custom() if x["id"] != b["id"]] + [b]
    home._write("brains.json", lst)
    return {"success": True, "brain": public(b)}


def remove_custom(bid):
    home._write("brains.json", [x for x in custom() if x["id"] != bid])
    k = _keys()
    k.pop(bid, None)
    home._write("keys.json", k)
    if home.settings().get("brain") == bid:
        home.save_settings({"brain": "claude-code"})
    return {"success": True}


def set_key(bid, key):
    k = _keys()
    if key:
        k[bid] = key.strip()
    else:
        k.pop(bid, None)
    home._write("keys.json", k)
    return {"success": True, "has_key": bool(key)}


# ---------- shared plumbing ----------

def tool_env():
    return {"AC_APPROVALS": "1", "AGENT_COMPOSER_HOME": home.HOME}


def tool_command():
    uv = shutil.which("uv") or "uv"
    return [uv, "run", "--quiet", "--script", os.path.join(ROOT, "mcp_server.py")]


def mcp_config():
    """A standard mcpServers file, for Claude Code and for your own harness."""
    p = os.path.join(home.path("state"), "mcp.json")
    cmd = tool_command()
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"mcpServers": {SERVER: {"command": cmd[0], "args": cmd[1:], "env": tool_env()}}}, f, indent=2)
    return p


def _start(args, env=None, stdin_text=None):
    errlog = open(os.path.join(home.path("state"), "brain-stderr.log"), "w+b")
    proc = subprocess.Popen(args, cwd=home.path("state"), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=errlog, env=env or dict(os.environ), creationflags=NO_WINDOW)
    with _lock:
        _run["proc"] = proc
    if stdin_text is not None:
        proc.stdin.write(stdin_text.encode("utf-8"))
    proc.stdin.close()
    return proc, errlog


def _finish(proc, errlog, emit, quiet_codes=(0, 1)):
    proc.wait()
    with _lock:
        _run["proc"] = None
    if proc.returncode not in quiet_codes and not _run["cancel"].is_set():
        errlog.seek(0)
        err = errlog.read().decode("utf-8", "replace")[-400:]
        if err.strip():
            emit({"type": "error", "text": err})
    errlog.close()


def _ok(body):
    return '"success": false' not in str(body).replace("'", '"').lower()


def _first_turn(text, session_id):
    return text if session_id else PERSONA + "\n\n---\n\n" + text


def stop():
    _run["cancel"].set()
    with _lock:
        p = _run["proc"]
    if p and p.poll() is None:
        if os.name == "nt":
            subprocess.call(["taskkill", "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            p.kill()
    return True


# ---------- stream readers (shared by built-ins and cli harnesses) ----------

def read_claude(proc, emit, sid):
    prefix = "mcp__%s__" % SERVER
    streamed = False
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
                    emit({"type": "tool", "id": b["id"], "name": b["name"].replace(prefix, ""), "input": b.get("input")})
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
                    emit({"type": "tool_done", "id": b.get("tool_use_id"), "ok": not b.get("is_error") and _ok(body), "summary": body[:400]})
        elif t == "result":
            sid = ev.get("session_id") or sid
            if ev.get("is_error"):
                emit({"type": "error", "text": str(ev.get("result") or ev.get("subtype"))[:400]})
    return sid


def read_codex(proc, emit, sid):
    for raw in proc.stdout:
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        t = ev.get("type")
        it = ev.get("item") or {}
        if t == "thread.started":
            sid = ev.get("thread_id") or sid
            emit({"type": "session", "id": sid})
        elif t in ("item.started", "item.completed") and it.get("type") == "mcp_tool_call":
            if t == "item.started":
                emit({"type": "tool", "id": it.get("id"), "name": it.get("tool"), "input": it.get("arguments")})
            else:
                res = it.get("result") or {}
                body = " ".join(x.get("text", "") for x in res.get("content", []) if isinstance(x, dict)) if res else ""
                err = (it.get("error") or {}).get("message")
                emit({"type": "tool_done", "id": it.get("id"), "ok": not err and _ok(body), "summary": (err or body)[:400]})
        elif t == "item.completed" and it.get("type") == "agent_message":
            emit({"type": "text", "delta": (it.get("text") or "") + "\n\n"})
        elif t in ("error", "turn.failed"):
            msg = ev.get("message") or (ev.get("error") or {}).get("message") or t
            emit({"type": "error", "text": str(msg)[:400]})
    return sid


def read_opencode(proc, emit, sid):
    prefix = SERVER + "_"
    told = False
    for raw in proc.stdout:
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        part = ev.get("part") or {}
        s = ev.get("sessionID") or part.get("sessionID")
        if s and s != sid:
            sid = s
        if sid and not told:
            told = True
            emit({"type": "session", "id": sid})
        t = ev.get("type")
        if t == "text" and part.get("text"):
            emit({"type": "text", "delta": part["text"] + "\n\n"})
        elif t == "tool_use" or part.get("type") == "tool":
            state = part.get("state") or {}
            cid = part.get("callID") or part.get("id")
            name = str(part.get("tool", "")).replace(prefix, "")
            emit({"type": "tool", "id": cid, "name": name, "input": state.get("input")})
            if state.get("status") in ("completed", "error"):
                body = str(state.get("output") or state.get("error") or "")
                emit({"type": "tool_done", "id": cid, "ok": state["status"] == "completed" and _ok(body), "summary": body[:400]})
        elif t == "error":
            emit({"type": "error", "text": json.dumps(ev.get("error") or ev)[:400]})
    return sid


def read_text(proc, emit, sid):
    for raw in proc.stdout:
        emit({"type": "text", "delta": raw.decode("utf-8", "replace")})
    return sid or uuid.uuid4().hex


READERS = {"claude": read_claude, "codex": read_codex, "opencode": read_opencode, "text": read_text}


# ---------- adapters ----------

def run_claude(b, text, sid, emit):
    exe = shutil.which("claude")
    args = [exe, "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--mcp-config", mcp_config(), "--strict-mcp-config", "--tools", "",
            "--allowedTools", "mcp__" + SERVER, "--permission-mode", "dontAsk",
            "--setting-sources", "project", "--append-system-prompt", PERSONA,
            "--model", home.settings().get("model") or "opus"]
    if sid:
        args += ["--resume", sid]
    env = dict(os.environ)
    if b["id"] == "claude-api":
        env["ANTHROPIC_API_KEY"] = api_key(b)
    else:
        env.pop("ANTHROPIC_API_KEY", None)  # the plan brain never bills a stray key
    proc, errlog = _start(args, env, text)
    sid = read_claude(proc, emit, sid)
    _finish(proc, errlog, emit)
    return sid


def _toml(s):
    return "'" + str(s).replace("'", "") + "'"


def run_codex(b, text, sid, emit):
    cmd = tool_command()
    pre = "mcp_servers.%s." % SERVER
    opts = ["--json", "--skip-git-repo-check", "--ignore-user-config", "-s", "read-only"]
    for f in ("shell_tool", "unified_exec", "apps", "browser_use", "computer_use", "plugins", "image_generation", "in_app_browser"):
        opts += ["--disable", f]  # contained: the FL tools only
    opts += ["-c", pre + "command=" + _toml(cmd[0]),
             "-c", pre + "args=[" + ",".join(_toml(a) for a in cmd[1:]) + "]",
             "-c", pre + "env={" + ",".join("%s=%s" % (k, _toml(v)) for k, v in tool_env().items()) + "}",
             "-c", pre + "default_tools_approval_mode='approve'"]
    if b.get("model"):
        opts += ["-m", b["model"]]
    args = [shutil.which("codex"), "exec"] + opts + (["resume", sid, "-"] if sid else ["-"])
    proc, errlog = _start(args, None, _first_turn(text, sid))
    sid = read_codex(proc, emit, sid)
    _finish(proc, errlog, emit)
    return sid


def run_opencode(b, text, sid, emit):
    cmd = tool_command()
    cfg = {"$schema": "https://opencode.ai/config.json",
           "mcp": {SERVER: {"type": "local", "command": cmd, "environment": tool_env(), "enabled": True}},
           "tools": {"*": False, SERVER + "_*": True},
           "permission": {"edit": "deny", "bash": "deny", "webfetch": "deny"}}
    p = os.path.join(home.path("state"), "opencode.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    env = dict(os.environ, OPENCODE_CONFIG=p)
    args = [shutil.which("opencode"), "run", "--format", "json"]
    if b.get("model"):
        args += ["--model", b["model"]]
    if sid:
        args += ["--session", sid]
    args.append(_first_turn(text, sid))
    proc, errlog = _start(args, env)
    sid = read_opencode(proc, emit, sid)
    _finish(proc, errlog, emit)
    return sid


def run_cli(b, text, sid, emit):
    fill = {"{prompt}": _first_turn(text, sid), "{mcp_config}": mcp_config(), "{session}": sid or "", "{model}": b.get("model", "")}
    args = []
    for a in b["command"]:
        for k, v in fill.items():
            a = a.replace(k, v)
        args.append(a)
    if not sid:  # drop "--resume" style pairs whose value is empty
        args = [a for i, a in enumerate(args) if a and not (i + 1 < len(args) and args[i + 1] == "" and a.startswith("-"))]
    args[0] = shutil.which(args[0]) or args[0]
    proc, errlog = _start(args, None, _first_turn(text, sid) if b.get("stdin") else None)
    sid = READERS[b.get("format", "text")](proc, emit, sid)
    _finish(proc, errlog, emit)
    return sid


class MCPClient:
    """Just enough of the MCP stdio protocol to list and call the FL tools."""

    def __init__(self):
        env = dict(os.environ, **tool_env())
        self.p = subprocess.Popen(tool_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, env=env, creationflags=NO_WINDOW)
        with _lock:
            _run["proc"] = self.p
        self.n = 0
        self.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "agent-composer", "version": "0.3.0"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg):
        self.p.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
        self.p.stdin.flush()

    def call(self, method, params):
        self.n += 1
        self._send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        for raw in self.p.stdout:
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(msg["error"].get("message", "tool error"))
                return msg.get("result", {})
        raise RuntimeError("The FL tools stopped.")

    def close(self):
        with _lock:
            _run["proc"] = None
        try:
            self.p.stdin.close()
            self.p.wait(timeout=3)
        except Exception:
            self.p.kill()


def _thread_path(sid):
    return os.path.join(home.path("state", "threads"), "".join(c for c in sid if c.isalnum()) + ".json")


def run_openai(b, text, sid, emit):
    sid = sid or uuid.uuid4().hex
    emit({"type": "session", "id": sid})
    try:
        with open(_thread_path(sid), encoding="utf-8") as f:
            msgs = json.load(f)
    except (OSError, ValueError):
        msgs = [{"role": "system", "content": PERSONA}]
    msgs.append({"role": "user", "content": text})
    mcp = MCPClient()
    try:
        tools = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", "")[:1000],
                                                   "parameters": t.get("inputSchema") or {"type": "object", "properties": {}}}}
                 for t in mcp.call("tools/list", {}).get("tools", [])]
        url = b["base_url"].rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        key = api_key(b)
        if key:
            headers["Authorization"] = "Bearer " + key
        for _ in range(16):
            if _run["cancel"].is_set():
                break
            body = json.dumps({"model": b["model"], "messages": msgs, "tools": tools, "stream": True}).encode("utf-8")
            try:
                resp = urllib.request.urlopen(urllib.request.Request(url, body, headers), timeout=180)
            except urllib.error.HTTPError as e:
                emit({"type": "error", "text": "%s said %s: %s" % (b["name"], e.code, e.read().decode("utf-8", "replace")[:300])})
                break
            except urllib.error.URLError as e:
                emit({"type": "error", "text": "Couldn't reach %s (%s)." % (b["name"], e.reason)})
                break
            content, calls = "", {}
            with resp:
                for raw in resp:
                    if _run["cancel"].is_set():
                        break
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        ch = json.loads(data)["choices"][0]
                    except (ValueError, KeyError, IndexError):
                        continue
                    d = ch.get("delta") or {}
                    if d.get("content"):
                        content += d["content"]
                        emit({"type": "text", "delta": d["content"]})
                    for tc in d.get("tool_calls") or []:
                        slot = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "args": ""})
                        slot["id"] = tc.get("id") or slot["id"]
                        fn = tc.get("function") or {}
                        slot["name"] += fn.get("name") or ""
                        slot["args"] += fn.get("arguments") or ""
            msg = {"role": "assistant", "content": content}
            if calls:
                msg["tool_calls"] = [{"id": c["id"] or "call_%d_%d" % (i, int(time.time())), "type": "function",
                                      "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                                     for i, c in sorted(calls.items())]
            msgs.append(msg)
            if not calls:
                break
            if content:
                emit({"type": "text", "delta": "\n\n"})
            for tc in msg["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except ValueError:
                    args = {}
                emit({"type": "tool", "id": tc["id"], "name": tc["function"]["name"], "input": args})
                try:
                    res = mcp.call("tools/call", {"name": tc["function"]["name"], "arguments": args})
                    out = " ".join(x.get("text", "") for x in res.get("content", []) if isinstance(x, dict))
                    ok = not res.get("isError") and _ok(out)
                except RuntimeError as e:
                    out, ok = str(e), False
                emit({"type": "tool_done", "id": tc["id"], "ok": ok, "summary": out[:400]})
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out[:20000]})
    finally:
        mcp.close()
        with open(_thread_path(sid), "w", encoding="utf-8") as f:
            json.dump(msgs[-80:] if len(msgs) > 80 else msgs, f)
    return sid


ADAPTERS = {"claude": run_claude, "codex": run_codex, "opencode": run_opencode, "openai": run_openai, "cli": run_cli}


def run(text, session_id, emit):
    """One chat turn on the plugged-in brain. Returns the session id."""
    _run["cancel"].clear()
    b = get(home.settings().get("brain"))
    ready, why = check(b)
    if not ready:
        emit({"type": "error", "text": "%s isn't ready: %s" % (b["name"], why)})
        return session_id
    sessions = home._read("sessions.json", [])
    old = next((x for x in sessions if x["id"] == session_id), None)
    if old and old.get("brain", "claude-code") != b["id"]:
        session_id = None  # a chat started on another brain can't continue here; start fresh
    sid = ADAPTERS[b["kind"]](b, text, session_id, emit)
    if sid:
        s = [x for x in sessions if x["id"] != sid]
        s.insert(0, {"id": sid, "title": (old or {}).get("title") or text[:60], "at": time.time(), "brain": b["id"]})
        home._write("sessions.json", s[:50])
    return sid
