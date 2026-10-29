# Agent Composer

**Talk to your FL Studio project.** Agent Composer is a chat window that sits next to FL Studio. You ask for a kick pattern, a tempo change, a melody or a look at your plugins, and an AI agent does it inside the open project. It asks first, and every change is one undo step.

> Created by **Mark Royal**. Built by **Jelly**, the Claude-powered agent of **Tech-Ants LLC**, for **Loboi Recordz LLC**. See [CREDITS.md](CREDITS.md).

```
 you ──► chat window ──► your brain (Claude, Codex, OpenCode, DeepSeek, local…) ──► agent-composer tools ──► file bridge ──► script inside FL Studio
```

## What it does

| | |
|---|---|
| **Chat** | Plain, Claudian-style chat with streaming replies, live tool rows and Stop. Past chats resume. `/` gives instant commands (`/play`, `/stop`, `/undo`, `/snapshot`, `/dock`, `/new`) that cost no AI tokens. |
| **Approve before anything moves** | Every change shows a card: *Okay to do this?* Approve or "Not that". You can switch this off in Settings › Safety & feel. Saving the project is off unless you allow it. |
| **VST Dock** | Every channel's plugin in one list: next/previous preset, live knobs, and 📌 parking for your go-to plugins. The agent can read and turn the same knobs. |
| **Piano roll writer** | Ask for a melody, chords or a bassline. You get a `.mid` file to drag in, and the notes queue for the **Agent Composer** piano-roll script (Piano roll › Tools › Scripting). |
| **Takes folder** | Drop vocal takes into `Documents/Agent Composer/Takes`. Play, rename, and ask the agent about them. |
| **Voice** | A mic button turns speech into a message (browser speech-to-text, nothing to install). Replies can be read aloud by the system voice or by your own voice server. |
| **Any brain** | Plug in a brain under Settings › Brain: Claude Code, Claude API, Codex, OpenCode, DeepSeek or a local model through Ollama. Each one runs on **your own** account or key. Or paste your own, the way you'd paste an MCP server: any OpenAI-compatible API or any agent harness. See [docs/BRAINS.md](docs/BRAINS.md). |

The agent only gets the Agent Composer tools. It can't read your files, run commands or browse the web.

## Install (Windows)

You need:
1. **FL Studio 2024 or newer** (it has to support Python MIDI scripts).
2. **A brain**: [Claude Code](https://docs.claude.com/en/docs/claude-code) (run `claude` once and sign in), or Codex, OpenCode, a DeepSeek key or Ollama. See [docs/BRAINS.md](docs/BRAINS.md).
3. **[uv](https://docs.astral.sh/uv/)** and **Python 3.10+**.
4. **A virtual MIDI port** so FL loads the script, for example [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) with a port named `loopMIDI Port`.

Then:

```powershell
git clone https://github.com/<you>/agent-composer.git
cd agent-composer
powershell -ExecutionPolicy Bypass -File install.ps1
```

In FL Studio, open **Options › MIDI settings**, select `loopMIDI Port`, set **Controller type** to **Agent Composer**, and enable it. The script usually picks the port up by itself.

Then double-click **`start.bat`**. A small window opens. A green dot in the header means FL is linked.

To remove it: `powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall`.

### Use it from Claude Code or Claudian instead

The same tools work in any Claude Code session:

```bash
claude mcp add agent-composer --scope user -- uv run --script /path/to/agent-composer/mcp_server.py
```

There, Claude Code's own permission prompts do the asking.

## Try it without FL

Open `app/ui/index.html` straight in a browser. With no app behind it, it runs in **demo mode** with a scripted agent and sample data, so you can feel the interface.

## Project layout

```
app/server.py            the local app: serves the window, runs the brain, relays approvals
app/brains.py            the brains: Claude Code, Codex, OpenCode, API models, your own harness
app/ui/index.html        the whole interface (one file, no build step)
mcp_server.py            the agent's tools (MCP server)
ac.py                    the file bridge to FL, plus a CLI: python ac.py status | snapshot
home.py                  settings, dock, takes (Documents/Agent Composer)
midifile.py              writes .mid files with the standard library
fl/device_AgentComposer.py    the script that runs inside FL Studio
fl/Agent Composer.pyscript    the piano-roll paste script
```

More detail: [WHITEPAPER.md](WHITEPAPER.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## Known limits

- FL's scripting API can't load a new plugin, import audio into the playlist, or write piano-roll notes from a MIDI script. That's why the dock works with plugins already in the project, and why notes come as a `.mid` file plus a one-click piano-roll script.
- `set_tempo` uses an FL call marked experimental. The agent reads the project back to confirm.
- Tested on Windows 11 with FL Studio 2024. macOS should work with the IAC Driver in place of loopMIDI, but it's untested.

## License

[MIT](LICENSE). Fork it, change it, ship your own. The in-FL script started as a fork of [fl-studio-mcp](https://github.com/karl-andres/fl-studio-mcp) (MIT).

*Agent Composer is an independent project. It isn't affiliated with or endorsed by Image-Line. FL Studio is a trademark of Image-Line Software.*
