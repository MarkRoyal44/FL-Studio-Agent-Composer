# Changelog

All notable changes to Agent Composer. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions: [SemVer](https://semver.org/).

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
