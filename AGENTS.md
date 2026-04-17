# AGENTS.md

## Project

CLI chat client for local Ollama with WordNet data loaded at startup. Entry point: `main.py` → `main()`.
On startup, loads `wordnet.db` (Princeton WordNet 3.1 in SQLite) into memory via `wordnet/` package, then connects to Ollama.

## Runtime prerequisite

A local Ollama server must be running; `main()` calls `client.list()` on startup and exits if unreachable.

## Toolchain

- Package manager: **uv**
- Python: **3.14** (pinned in `.python-version`)
- Depends on: `ollama>=0.6.1`, `python-dotenv>=1.2.2`
- No tests, CI, or linting configured yet

## Commands

```bash
uv run python main.py                    # run with default model (exaone3.5:latest)
uv run python main.py --model llama3.2   # override model via flag
uv run python main.py --wordnet-db /path/to/wordnet.db   # override wordnet.db location
uv add <package>                          # add a dependency
```

## Configuration

Copy `.env.example` to `.env` to set defaults:
- `OLLAMA_MODEL` — default model (falls back to `exaone3.5:latest`)
- `OLLAMA_HOST` — Ollama server URL (falls back to `http://localhost:11434`)

Precedence: `--model` flag > `OLLAMA_MODEL` env > hardcoded default.

## Code style notes

- `load_dotenv()` is called at module level (line 7) — runs on import, not just on `__main__`.
- `OLLAMA_HOST` is read via `__import__("os")` inline in `main()` rather than a top-level import. This is existing style, not a bug to fix.
- `.env` is not listed in `.gitignore` — avoid committing it.

## WordNet data

- `wordnet.db` (~70MB SQLite) is gitignored — must be present at project root or passed via `--wordnet-db`
- Source: Princeton WordNet 3.1, converted by [wordnet-to-db](https://github.com/chasangchual/wordnet-to-db)
- Loaded into memory as `WordNetData` dataclass (`wordnet/__init__.py`) with 8 entity lists:
  `lexical_domains`, `synsets`, `words`, `senses`, `semantic_relations`, `morph_exceptions`, `verb_frames`, `verb_frame_senses`
- Key relations: `@` hypernym, `~` hyponym, `!` antonym, `&` similar — see wordnet-to-db README for full symbol table