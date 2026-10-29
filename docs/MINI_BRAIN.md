# Mini Brain

Your own notes, kept on your computer, that the agent can search before it answers. This is your brain, not ours: Agent Composer ships it empty.

## Add documents

- **Settings › Mini Brain › Add documents**: drop files in, or tap to pick them.
- Or put files straight into `Documents/Agent Composer/Mini Brain` with Explorer.

It reads `.txt` `.md` `.csv` `.tsv` `.json` `.lrc` `.srt` `.vtt` `.html` `.xml` `.rtf` `.yaml` `.docx` and `.pdf`, up to 25 MB each. Scanned PDFs (pictures of pages) have no text inside them, so their card says so. Save those as `.txt` or `.docx`.

Good things to drop in: your lyrics, a style or sound guide ("808s tuned to the key, swing at 58%"), song ideas, references, a gear list, notes from a session.

## How the agent uses it

Every brain (Claude Code, Codex, OpenCode, DeepSeek, Ollama, your own) gets three read-only tools:

| Tool | Does |
|---|---|
| `brain_list` | lists your documents |
| `brain_search` | finds the best excerpts for some keywords |
| `brain_read` | reads one document, 4,000 characters at a time |

When you have documents and Brain mode is on, the agent is told to check them whenever a request depends on your taste or your past work, and to say which document it used. Try: *"write a hook in my style"* or *"what mic do I own?"*

## Privacy

- Files never leave your computer by themselves. While answering, the agent reads excerpts, and those go only to the brain you plugged in.
- The agent can't write, rename or delete anything in the Mini Brain. Only you can.
- Switch **Brain mode** off and the tools answer "switched off".
- The extracted text is cached in `Documents/Agent Composer/state/minibrain/`. Delete that folder any time and it rebuilds.

## For contributors

`minibrain.py` is standard library only. Search is keyword scoring over overlapping 4,000-character parts with light word stemming. Smarter search (local embeddings) is on the roadmap. It has to stay offline and optional.
