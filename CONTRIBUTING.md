# Contributing

Thanks for wanting to make Agent Composer better. It's meant to be forked, remixed and improved.

## Ground rules
- **Keep the main screen plain.** New features go behind the gear in Settings unless they're part of chatting.
- **Every change to a project asks first and is one undo step.** New tools that change FL must go through `_change()` in `mcp_server.py` and `_undo_step()` in the FL script.
- **No `eval`, ever.** The FL script runs only exact, allow-listed action names.
- **Standard library only** in `app/`, `ac.py`, `home.py` and `midifile.py`. The only dependency is `mcp`, used by the tool server.
- **Say what's not possible.** If FL's API can't do something, the tool should say so plainly instead of pretending.

## Adding a tool
1. If FL needs a new action, add a handler in `fl/device_AgentComposer.py` and register it in the dispatcher.
2. Add the action name to `ALLOWED` in `mcp_server.py`.
3. Add a typed `@mcp.tool()` with a docstring the model can follow. Wrap changes in `_change("plain summary", action, params)`.
4. Give it a friendly label in `PRETTY` in `app/ui/index.html`.
5. Note it in `CHANGELOG.md` under *Unreleased*.

## Testing
- `python ac.py status` shows whether FL's script is alive.
- `python app/server.py --no-open`, then open the printed address.
- Open `app/ui/index.html` straight from disk to check the interface in demo mode.
- Reload the FL script after editing: in MIDI settings, disable and re-enable the port (no FL restart needed).

## Pull requests
Small and focused. Describe what changed, how you tested it in FL, and add a screenshot or GIF for UI changes.
