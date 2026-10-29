# Security

## How Agent Composer limits the agent
- The model gets **only** the Agent Composer tools. Built-in tools (files, shell, web) are switched off and other MCP servers are ignored (`--tools "" --strict-mcp-config`).
- The FL script runs **only exact, allow-listed action names** and never evaluates code from a command.
- Project changes wait for a human **Approve** in the app. The gate is enforced in the tool server.
- Saving the project is off by default.
- The app listens on **127.0.0.1 only**, and every POST needs a custom header, so other websites can't drive it from your browser.
- The Claude Code brain removes any `ANTHROPIC_API_KEY` from its environment so it runs on your plan; the Claude API brain uses that key only when you choose it.

## Reporting a problem
Please don't open a public issue for a security problem. Email the maintainers through the contact on the GitHub profile that hosts this repo, with steps to reproduce. You'll get an answer within a week.
