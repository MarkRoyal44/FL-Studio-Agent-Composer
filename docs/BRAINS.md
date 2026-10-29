# Brains

A brain is the AI that does the thinking. Agent Composer doesn't ship one. Each brain runs on **your own** account or key, through apps already on your computer. Every brain gets the same FL tools and nothing else, and every change still goes through the approval card.

Pick one in **Settings › Brain**.

| Brain | Runs on | You need |
|---|---|---|
| **Claude Code** | your Claude plan | [Claude Code](https://docs.claude.com/en/docs/claude-code), signed in once with `claude` |
| **Claude API** | your Anthropic key, pay as you go | a key, pasted in Settings or set as `ANTHROPIC_API_KEY` |
| **Codex** | your ChatGPT plan | the [Codex CLI](https://github.com/openai/codex), signed in once with `codex login` |
| **OpenCode** | any provider you've set up in OpenCode | [OpenCode](https://opencode.ai), signed in once with `opencode auth login` |
| **DeepSeek** | your DeepSeek key | a key, pasted in Settings or set as `DEEPSEEK_API_KEY` |
| **Local (Ollama)** | your own computer, free and offline | [Ollama](https://ollama.com) plus a model that supports tools, such as `ollama pull qwen3:8b` |

If a brain isn't set up yet, its card says what's missing.

## How each one is kept to the FL tools

- **Claude Code**: `--tools ""`, `--strict-mcp-config`, and only `mcp__agent-composer` is allowed.
- **Codex**: your `config.toml` is ignored, the sandbox is read-only, and shell, apps, browser, computer use, plugins and image generation are switched off. Only the agent-composer tools are loaded.
- **OpenCode**: a private config turns every built-in tool off (`"*": false`) and denies edit, bash and webfetch.
- **API brains** (DeepSeek, Ollama, your own): Agent Composer runs the conversation itself and only ever offers the model the FL tools.

## Add your own

Open **Settings › Brain › Add your own brain**, paste one JSON object and click **Plug it in**. It works the same way as pasting an MCP server.

### Any OpenAI-compatible API

OpenRouter, Groq, Together, Mistral, LM Studio, vLLM, your own server:

```json
{
  "name": "OpenRouter",
  "kind": "openai",
  "base_url": "https://openrouter.ai/api/v1",
  "model": "deepseek/deepseek-chat",
  "api_key_env": "OPENROUTER_API_KEY"
}
```

| Field | Meaning |
|---|---|
| `base_url` | the address that ends just before `/chat/completions` |
| `model` | the model name that service expects |
| `api_key_env` | the environment variable that holds your key (recommended) |
| `api_key` | or paste the key itself. It's moved into `keys.json` and never shown again |

The model has to support tool calling (function calling).

### Your own harness

Any command-line agent that can load an MCP config:

```json
{
  "name": "My harness",
  "kind": "cli",
  "command": ["my-agent", "--mcp-config", "{mcp_config}", "--resume", "{session}", "{prompt}"],
  "format": "text"
}
```

| Placeholder | Filled with |
|---|---|
| `{prompt}` | the message (the first turn also carries the Agent Composer persona) |
| `{mcp_config}` | the path to a standard `{"mcpServers": {...}}` file with the FL tools |
| `{session}` | the session id to resume. A flag followed by an empty value is dropped on the first turn |
| `{model}` | the brain's `model` field |

Set `"stdin": true` to send the prompt on stdin instead.

`format` tells Agent Composer how to read the output:
- `text`: plain text is shown as it arrives
- `claude`: Claude Code `stream-json`, which suits forks of Claude Code
- `codex`: `codex exec --json` events
- `opencode`: `opencode run --format json` events

With `text`, tool calls aren't shown as rows, but the approval cards still pop up because the gate lives in the tool server.

## Where things are saved

| File | Holds |
|---|---|
| `Documents/Agent Composer/state/brains.json` | your custom brains, with no keys, so it's safe to share |
| `Documents/Agent Composer/state/keys.json` | keys you pasted in Settings |

Neither file is inside the repo.

## Adding a built-in brain (for contributors)

1. Write `run_<kind>(brain, text, session_id, emit)` in `app/brains.py`. It turns that brain's output into the events `session`, `text`, `tool`, `tool_done` and `error`, and returns the session id.
2. Add it to `ADAPTERS`, `KINDS` and `check()`, and add a card to `BUILTIN`.
3. Keep the brain to the FL tools: no shell, no file access, no other MCP servers.
