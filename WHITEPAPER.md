# Agent Composer: an AI agent that works inside your DAW

**White paper, version 0.3, October 2026**
Created by Mark Royal · Built by Jelly (Tech-Ants LLC) · For Loboi Recordz LLC

---

## Abstract

Music producers already talk to AI about their songs. They ask for chord ideas, drum patterns and mix advice. Then they go back to the DAW and click everything in by hand. The advice lives in one window and the work lives in another.

Agent Composer closes that gap. It is a small chat window, connected to FL Studio, where an AI agent reads the open project and acts on it: setting tempo, writing step patterns, creating patterns and markers, adjusting mixer tracks, turning plugin knobs and writing notes. Every change waits for the producer's approval and lands as a single undo step.

This paper explains the problem, the design principles, the architecture, the safety model and the roadmap.

## 1. The problem

**The copy-paste tax.** A chat assistant can describe a four-on-the-floor kick, but the producer still clicks sixteen steps. It can suggest an A-minor arpeggio, but the producer still draws it note by note. Most of the value is lost in that last step.

**Assistants can't see the project.** A general chatbot doesn't know the tempo, which channels exist, or that the lead synth is Serum on channel 2. Its advice is generic because its context is empty.

**Control is the real fear.** Producers protect their sessions. A tool that changes a project without asking, or makes changes that can't be undone, won't be trusted twice.

## 2. Thesis

> The best AI music tool isn't a generator that replaces the producer. It's a studio assistant that sits in the room, reads the session, does the clicking, and always asks before touching the mix.

Agent Composer is built around three promises:

1. **It reads before it writes.** The agent pulls a snapshot of the project before every change and again after, to confirm.
2. **It asks before it acts.** Every change becomes an approval card. Saving is off by default.
3. **It can always be undone.** Each action is wrapped as exactly one FL undo step.

## 3. Design principles

**Plain first.** The main screen is only a chat, modelled on Claudian (Claude inside Obsidian): messages, one input box, a brain chip, speaker, mic and send. Everything else (brains, VST dock, notes, takes, voice, project, safety) lives behind one gear, in one Settings box.

**Neutral and warm.** The interface uses calm grays so it sits beside any FL skin, one soft sky-blue accent, and warm amber for anything that needs the producer's attention. Studios are dark rooms and long sessions, so contrast is gentle.

**Game feel.** Small, fast, physical feedback makes software feel friendly. These are the same "juice" techniques games use:
- buttons squash when pressed and spring back,
- messages pop in with a slight overshoot,
- tool rows spin while working, then snap to a check with a little burst of sparks,
- approval cards nudge in and chime twice, so a request is hard to miss,
- numbers roll to new values instead of jumping,
- quiet WebAudio clicks and chimes, with an off switch,
- reduced-motion settings are respected.

None of it slows the work down. Every effect finishes in under half a second.

**Honest limits.** Where FL's API can't do something, the interface says so and offers the next best route.

## 4. Architecture

```
┌─────────────┐   HTTP (localhost)   ┌──────────────┐   stdio   ┌───────────────┐
│ Chat window │ ───────────────────► │  app server  │ ────────► │  Claude Code  │
│ (index.html)│ ◄─── NDJSON stream ─ │ (server.py)  │ ◄──────── │  (-p, stream) │
└─────────────┘                      └──────┬───────┘           └──────┬────────┘
       ▲  approval cards                    │ approvals folder         │ MCP (stdio)
       └────────────────────────────────────┤◄─────────────────────────┤
                                            │                   ┌──────▼────────┐
                                            │                   │ mcp_server.py │
                                            │                   └──────┬────────┘
                                            │   file bridge (JSON)     │
                                            └──────────────┬───────────┘
                                                    ┌──────▼──────────────────┐
                                                    │ device_AgentComposer.py │
                                                    │ (inside FL Studio)      │
                                                    └─────────────────────────┘
```

**Inside FL.** FL Studio runs Python MIDI controller scripts. Agent Composer's script loads on a virtual MIDI port and, on every idle tick, checks a small `command.json` file. It runs the named action, but only if the name is on an exact allow-list. Nothing in a command is ever evaluated as code. It writes `response.json` carrying the command's id, so a caller never reads a stale answer. A `status.json` heartbeat proves the script is alive.

**The tools.** `mcp_server.py` is a Model Context Protocol server. It exposes typed tools such as `get_project_snapshot`, `set_tempo`, `set_step_sequence`, `write_notes`, `list_plugins` and `set_plugin_param`, plus a guarded `run_action` for the rest of the allow-list. Any MCP client can use it, including Claude Code, Claudian and Claude Desktop.

**The brain.** The app runs Claude Code in headless mode (`claude -p --output-format stream-json`) with only the Agent Composer tools available: built-in tools are off and other MCP servers are ignored. Replies stream back token by token. Conversations resume by session id.

**The app.** `server.py` is standard-library Python. It serves the window, streams each turn to the browser as newline-delimited JSON, and relays approvals. It opens as a chromeless Edge or Chrome app window, so there's nothing extra to install.

**Notes.** FL's MIDI-script API can't write piano-roll notes. `write_notes` does two things instead. It writes a standard `.mid` file, using a dependency-free encoder. It also queues the notes as JSON for a piano-roll script, which pastes them with one click from Tools › Scripting.

## 5. Safety model

| Layer | What it stops |
|---|---|
| Exact allow-list inside FL | Arbitrary code; unknown actions |
| Only Agent Composer tools offered to the model, on every brain | File access, shell commands, web access |
| Approval gate in the tool server | Any project change without a human Approve |
| Save off by default | Overwriting the project file |
| One undo step per action | Changes that can't be reversed |
| Localhost-only server with a required custom header | Other websites driving the app through the browser |

The approval gate lives in the tool server, not the UI. A change can't skip it even if the model tries. A request nobody answers expires after three minutes and changes nothing.

## 6. The battery model

The brain is a swappable cell, and Agent Composer doesn't bring one of its own. Producers plug in what they already pay for or run:
- Claude Code or the Claude API,
- Codex,
- OpenCode,
- DeepSeek,
- a free local model through Ollama.

Each brain is kept to the FL tools. Claude Code has its built-in tools off. Codex runs without shell, apps or browser. OpenCode has every built-in tool off. For API models, Agent Composer runs the tool loop itself and offers only the FL tools.

A producer can also paste their own brain the way they would paste an MCP server. That can be any OpenAI-compatible API, or any agent harness that reads a standard MCP config. The tools, approvals and UI stay the same whichever brain is plugged in, because the tools are a standard protocol, not a private API.

## 7. Limits

- FL's API can't load plugins, import audio into the playlist or write piano-roll notes from a controller script (see §4 for the workaround).
- Tempo changes use an FL call marked experimental, so the agent always confirms with a fresh snapshot.
- The app is tested on Windows 11 with FL Studio 2024. macOS is expected to work with the IAC Driver but is untested.
- Voice input uses the browser's speech recognition, which may send audio to the browser vendor's service. A local voice server can be plugged in for speech output today, and for input later.

## 8. Roadmap

1. **Signed one-click installer** that bundles the window as a desktop app.
2. **Brain presets to share**: export a custom brain card for others to paste, with no keys inside.
3. **Local speech-to-text** (Whisper-class) through the voice server socket.
4. **Arrangement awareness:** reading playlist clips and markers for song-structure requests.
5. **Takes intelligence:** automatic take naming and comparing takes by loudness and timing.
6. **Mini Brain search by meaning:** optional local embeddings next to the keyword search, with no extra cloud service.
7. **Shared presets:** export and import a producer's parked dock and safety settings.

## 9. Credits

- **Mark Royal**: creator, product direction and taste.
- **Jelly**: the Claude-powered agent at Tech-Ants LLC that designed and built this release.
- **Tech-Ants LLC**: engineering home.
- **Loboi Recordz LLC**: the label and studio it was built for.
- **fl-studio-mcp** by calvinw and Karl Andres (MIT): the starting point for the in-FL script.

Agent Composer is independent. It isn't affiliated with Image-Line. FL Studio is a trademark of Image-Line Software.
