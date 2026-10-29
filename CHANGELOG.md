# Changelog

All notable changes to Agent Composer. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions: [SemVer](https://semver.org/).

## [0.4.0] - 2026-10-29
### Added
- **Mini Brain**: the person's own documents, searchable by every brain. Settings › Mini Brain takes drag-and-drop uploads (.txt .md .docx .pdf .csv .lrc .srt .html .rtf and more) into `Documents/Agent Composer/Mini Brain`. Files dropped into that folder in Explorer count too.
- Tools `brain_list`, `brain_search`, `brain_read` (read-only). The persona tells the agent to check them when a request depends on the person's taste or past work, and to name the document it used.
- **Brain mode** switch to turn document reading off.
- `minibrain.py`: standard-library text extraction (including .docx and most text PDFs), cached in `state/minibrain/`, plus keyword search.

## [0.3.0] - 2026-10-29
### Added
- Six live brains in Settings › Brain: Claude Code, Claude API, Codex, OpenCode, DeepSeek and Local (Ollama). Each runs on the person's own account or key and gets only the FL tools. See [docs/BRAINS.md](docs/BRAINS.md).
- **Add your own brain**: paste one JSON object for any OpenAI-compatible API or any CLI harness that reads an MCP config. Templates are included.
- `app/brains.py`: brain adapters, a stdlib MCP client and the OpenAI-compatible tool loop.
- API keys pasted in Settings are kept in `state/keys.json` and never sent back to the window.

### Changed
- Brain cards show what's missing ("SET UP") instead of "SOON".
- Past chats remember which brain they started on.

## [0.2.0] - 2026-10-29
### Added
- Desktop app (`app/server.py` + `app/ui/index.html`): a Claudian-style chat window that runs Claude Code with only the Agent Composer tools. Streaming replies, live tool rows, Stop, past chats, `/` quick commands.
- Approval cards: every project change waits for Approve. The gate lives in the tool server.
- Settings box: Brain (battery cells + model), VST Dock, Notes, Takes, Voice, Project, Safety & feel.
- VST Dock: per-channel plugins, preset next/prev, live knobs, parking. Tools: `list_plugins`, `get_plugin_params`, `set_plugin_param`, `change_preset`, `park_plugin`.
- Piano roll writer: `write_notes` saves a `.mid` file and queues notes for the new `Agent Composer.pyscript` piano-roll script.
- Takes folder: `list_takes`, `rename_take`, playback in the app.
- Voice: browser speech-to-text, read-aloud, optional custom voice server.
- Gray, warm interface with game-feel feedback and soft sounds.
- `install.ps1`, `start.bat`, white paper and project docs.

### Changed
- `save_project` is refused from the app unless "Allow saving" is on.

## [0.1.0] - 2026-10-29
### Added
- In-FL script with a file bridge, heartbeat, project snapshot, patterns, markers, undo, save, tempo.
- MCP server with the first project tools, and the `ac.py` CLI.
