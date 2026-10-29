# Security

## How Agent Composer limits the agent
- On every brain, the model gets **only** the Agent Composer tools. Claude Code: `--tools "" --strict-mcp-config`. Codex: user config ignored, read-only sandbox, shell, apps and browser off. OpenCode: every built-in tool off. API brains: Agent Composer runs the loop and offers only the FL tools.
- Brains run on **your own** accounts and keys. Keys pasted in Settings are saved in `Documents/Agent Composer/state/keys.json`, outside the repo, and are never sent back to the window.
- The Mini Brain is **read-only** for the agent and limited to `Documents/Agent Composer/Mini Brain`. Uploads are reduced to a bare filename, so they can't land outside that folder. Excerpts go only to the brain you plugged in. Switch it off with Brain mode.
- The FL script runs **only exact, allow-listed action names** and never evaluates code from a command.
- Project changes wait for a human **Approve** in the app. The gate is enforced in the tool server.
- Saving the project is off by default.
- The app listens on **127.0.0.1 only**, and every POST needs a custom header, so other websites can't drive it from your browser.
- The Claude Code brain removes any `ANTHROPIC_API_KEY` from its environment so it runs on your plan; the Claude API brain uses that key only when you choose it.

## Reporting a problem
Please don't open a public issue for a security problem. Email the maintainers through the contact on the GitHub profile that hosts this repo, with steps to reproduce. You'll get an answer within a week.
