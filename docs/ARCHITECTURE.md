# Architecture

This is for developers who want to change Agent Composer. For the why, read the [white paper](../WHITEPAPER.md).

## Pieces

| File | Runs in | Job |
|---|---|---|
| `fl/device_AgentComposer.py` | FL Studio's Python (3.12, subinterpreter) | Polls the bridge in `OnIdle`, runs allow-listed actions, writes a heartbeat |
| `fl/Agent Composer.pyscript` | FL's piano-roll scripting | Pastes queued notes into the open piano roll |
| `ac.py` | any Python | Sends one command over the bridge and waits for the matching reply |
| `mcp_server.py` | `uv run --script` (stdio) | MCP tools for the model; the approval gate |
| `home.py` | imported | Settings, VST dock, takes, under `Documents/Agent Composer` |
| `minibrain.py` | imported | Mini Brain: text extraction, cache and keyword search over the person's documents |
| `midifile.py` | imported | Standard-library `.mid` writer |
| `app/server.py` | Python, localhost | Serves the UI, runs the brain per turn, streams events, relays approvals |
| `app/brains.py` | imported | Brain adapters (Claude, Codex, OpenCode, OpenAI-compatible, your own CLI) |
| `app/ui/index.html` | browser / Edge app window | The whole interface; falls back to demo mode with no server |

## The file bridge

Folder: `Documents/Image-Line/FL Studio/Settings/Hardware/AgentComposer/bridge/`

| File | Writer | Shape |
|---|---|---|
| `command.json` | caller | `{"id": "a1b2c3", "action": "tempo.set", "params": {"bpm": 140}}` |
| `response.json` | FL script | `{"id": "a1b2c3", "success": true, ...}` |
| `status.json` | FL script | heartbeat: `alive`, `ticks`, `project`, stdlib probe |
| `notes.json` | `write_notes` | `{"name": "...", "notes": [{"pitch": 60, "start": 0, "length": 1, "velocity": 0.8}]}` |

Writers use write-then-rename so a reader never sees half a file. FL's Python can't create folders, so the outside side creates them.

## One chat turn

1. The UI sends `POST /api/chat {"text", "session_id"}` with header `X-Agent-Composer: 1`.
2. The server starts `claude -p --output-format stream-json --verbose --include-partial-messages --mcp-config <state/mcp.json> --strict-mcp-config --tools "" --allowedTools mcp__agent-composer --permission-mode dontAsk --setting-sources project [--resume <id>]` and writes the message to stdin.
3. Claude's stream is turned into small NDJSON events for the UI:

| Event | Fields |
|---|---|
| `session` | `id` |
| `text` | `delta` |
| `tool` | `id`, `name` (prefix stripped), `input` |
| `tool_done` | `id`, `ok`, `summary` |
| `error` | `text` |
| `done` | `session_id` |

4. While the turn runs, the UI polls `GET /api/approvals` every 400 ms.

## Approvals

The app sets `AC_APPROVALS=1` for the tool server. A changing tool calls `_ask(summary, detail)`, which:
- writes `Documents/Agent Composer/state/approvals/<id>.ask.json`,
- waits up to 180 s for `<id>.answer.json` (`{"approved": true|false}`), which the UI writes through `POST /api/approvals/<id>`,
- runs the action on approve, or returns a "person rejected this" error the model is told to respect.

With approvals off (Settings › Safety & feel) or outside the app, `_ask` returns at once.

## HTTP API (localhost)

`GET` `/api/health` · `/api/brains` · `/api/snapshot` · `/api/settings` · `/api/approvals` · `/api/sessions` · `/api/dock` · `/api/params?channel=N` · `/api/takes` · `/api/minibrain` · `/api/midi` · `/takes/<file>`

`POST` (needs `X-Agent-Composer: 1`) `/api/chat` · `/api/stop` · `/api/brains` · `/api/brains/remove` · `/api/brains/key` · `/api/settings` · `/api/approvals/<id>` · `/api/park` · `/api/unpark` · `/api/preset` · `/api/param` · `/api/transport` · `/api/undo` · `/api/rename-take` · `/api/minibrain/add` · `/api/minibrain/remove` · `/api/open-folder`

Direct UI actions (preset, knob, transport, undo) skip the approval card because the person clicked them.

## Brains

`app/brains.py` holds the brains. `server.chat()` calls `brains.run()`, which picks the plugged-in brain and translates its output into the event table above.

| Kind | How it runs |
|---|---|
| `claude` | `claude -p --output-format stream-json`, as above |
| `codex` | `codex exec --json --ignore-user-config -s read-only`, with shell, apps and browser off, and the FL server passed with `-c mcp_servers.agent-composer.*` |
| `opencode` | `opencode run --format json`, with a private `OPENCODE_CONFIG` that turns every built-in tool off |
| `openai` | Agent Composer runs the loop: `/chat/completions` with streaming, plus a small stdio MCP client (`MCPClient`) that lists and calls the FL tools. Threads are stored in `state/threads/` |
| `cli` | your command, with `{prompt}`, `{mcp_config}`, `{session}` and `{model}` filled in; output read as `text`, `claude`, `codex` or `opencode` |

Custom brains: `GET /api/brains`, `POST /api/brains` with `{"brain": {...}}`, `POST /api/brains/remove`, `POST /api/brains/key`. Keys are never returned. Full format: [BRAINS.md](BRAINS.md).
