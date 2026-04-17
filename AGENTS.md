# AGENTS.md

## Project

CLI chat client for local Ollama. Entry point: `main.py` → `main()`.

## Toolchain

- Package manager: **uv**
- Python: **3.14** (pinned in `.python-version`)
- Depends on: `ollama`, `python-dotenv`
- No tests, CI, or linting configured yet

## Commands

```bash
uv run python main.py                    # run with default model (exaone3.5:latest)
uv run python main.py --model llama3.2   # override model via flag
uv add <package>                          # add a dependency
```

## Configuration

Copy `.env.example` to `.env` to set defaults:
- `OLLAMA_MODEL` — default model (falls back to `exaone3.5:latest`)
- `OLLAMA_HOST` — Ollama server URL (falls back to `http://localhost:11434`)

Precedence: `--model` flag > `OLLAMA_MODEL` env > hardcoded default.