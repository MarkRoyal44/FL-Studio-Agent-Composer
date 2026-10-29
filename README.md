# FL Studio Agent Composer

**Talk to your FL Studio project.** Agent Composer is a chat window that docks inside FL Studio. You ask for a kick pattern, a tempo change, a melody or a look at your plugins, and an AI agent does it inside the open project. It asks first, and every change is one undo step.

> Created by **Mark Royal**. Built by **Jelly**, the Claude-powered agent of **Tech-Ants LLC**, for **Loboi Recordz LLC**. See [CREDITS.md](CREDITS.md).

```
 you ──► chat window ──► your brain (Claude, Codex, OpenCode, DeepSeek, local…) ──► agent-composer tools ──► file bridge ──► script inside FL Studio
```

## What it does

| | |
|---|---|
| **Chat** | Plain, Claudian-style chat with streaming replies, live tool rows and Stop. Past chats resume. `/` gives instant commands (`/play`, `/stop`, `/undo`, `/snapshot`, `/dock`, `/new`) that cost no AI tokens. |
| **Approve before anything moves** | Every change shows a card: *Okay to do this?* Approve or "Not that". Hit **YOLO** in the header to auto-approve (like auto-approve in Claude Code); hit it again to go back. Saving the project is off unless you allow it. |
| **Docks inside FL** | The window pins itself inside FL's window, floats over your project and minimizes with FL, like FL's own plugin windows. Turn it off in Settings › Safety & feel. |
| **VST Dock** | Every channel's plugin in one list: next/previous preset, live knobs, and 📌 parking for your go-to plugins. The agent can read and turn the same knobs. |
| **Piano roll writer** | Ask for a melody, chords or a bassline. You get a `.mid` file to drag in, and the notes queue for the **Agent Composer** piano-roll script (Piano roll › Tools › Scripting). |
| **Takes folder** | Drop vocal takes into `Documents/Agent Composer/Takes`. Play, rename, and ask the agent about them. |
| **Mini Brain** | Your own notes in Settings › Mini Brain: drop in lyrics, song ideas, references, gear lists or a style guide (.txt .md .docx .pdf and more). Every brain can search them before it answers, and tells you which document it used. Files stay in `Documents/Agent Composer/Mini Brain`. See [docs/MINI_BRAIN.md](docs/MINI_BRAIN.md). |
| **Voice** | A mic button turns speech into a message (browser speech-to-text, nothing to install). Replies can be read aloud by the system voice or by your own voice server. |
| **Any brain** | Plug in a brain under Settings › Brain: Claude Code, Claude API, Codex, OpenCode, DeepSeek or a local model through Ollama. Each one runs on **your own** account or key. Or paste your own, the way you'd paste an MCP server: any OpenAI-compatible API or any agent harness. See [docs/BRAINS.md](docs/BRAINS.md). |

**New here?** Download the [one-file installer](https://github.com/MarkRoyal44/FL-Studio-Agent-Composer/releases/latest/download/AgentComposerSetup.exe) and follow the [2-minute tutorial](docs/TUTORIAL.md).

The agent only gets the Agent Composer tools. It can't read your files (only the documents you put in its Mini Brain), run commands or browse the web.

## Install (Windows): one download

1. Download **[AgentComposerSetup.exe](https://github.com/MarkRoyal44/FL-Studio-Agent-Composer/releases/latest/download/AgentComposerSetup.exe)**.
2. Double-click it. If Windows says *"Windows protected your PC"*, click **More info › Run anyway** (the installer isn't code-signed yet).
3. Answer **Y** when it offers loopMIDI. That's it.

Setup puts Agent Composer in your user folder and needs no admin rights, apart from loopMIDI's own installer. It gets the free helpers it needs: **uv**, which brings its own Python, and **loopMIDI**, the virtual MIDI port FL loads the script on. It also copies the scripts into FL Studio and adds **Agent Composer** to your desktop and Start menu. Remove it any time from **Settings › Apps**. Your files in `Documents/Agent Composer` are kept.

You still need:
- **FL Studio 2024 or newer** (it has to support Python MIDI scripts).
- **A brain**: Claude Code, Codex, OpenCode, a DeepSeek key, or a free local model with Ollama. The app's Brain tab says what each one needs. See [docs/BRAINS.md](docs/BRAINS.md).

**New here? Read the [2-minute tutorial](docs/TUTORIAL.md).** The same steps are in the app under **Settings › Start here**.

> **It's a plugin too.** Setup adds `Agent Composer.clap`, a CLAP plugin (the open plugin format FL 2024 reads, like VST). In FL: *Options › Manage plugins › Find installed plugins* once, then **Add › Agent Composer** opens the chat in a plugin window. It makes no sound. Prefer a separate window? The desktop shortcut opens one that docks inside FL. Your own VSTs show up in its **VST Dock** tab.

### Install from source (developers)

```powershell
git clone https://github.com/MarkRoyal44/FL-Studio-Agent-Composer.git
cd FL-Studio-Agent-Composer
powershell -ExecutionPolicy Bypass -File installer\setup.ps1
```

`installer\build.ps1` builds the setup exe from the committed code with IExpress, which is built into Windows.

### Use it from Claude Code or Claudian instead

The same tools work in any Claude Code session:

```bash
claude mcp add agent-composer --scope user -- uv run --script /path/to/FL-Studio-Agent-Composer/mcp_server.py
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

## Support

Agent Composer is free. If it saved you a session, tip on Cash App: **[$CASHTAG](https://cash.app/$CASHTAG)**. A ⭐ on this repo helps other producers find it. Bugs and ideas go in [Issues](https://github.com/MarkRoyal44/FL-Studio-Agent-Composer/issues). The same links are in the app under **Settings › ♥ Support**.

## License

[MIT](LICENSE). Fork it, change it, ship your own. The in-FL script started as a fork of [fl-studio-mcp](https://github.com/karl-andres/fl-studio-mcp) (MIT).

*FL Studio Agent Composer is an unofficial, independent project. It isn't affiliated with or endorsed by Image-Line. FL Studio is a trademark of Image-Line Software.*
