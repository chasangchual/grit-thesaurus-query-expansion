# Grit Thesaurus Query Expansion

CLI chat client for local Ollama that expands user prompts using WordNet before sending them to the LLM.

On every turn, the system extracts keywords from the full conversation history, looks up hyponyms (more specific words) and hypernyms (broader words) in Princeton WordNet 3.1, ranks the candidates by relevance, and asks the LLM to rewrite the user's prompt using the most fitting terms. The expanded prompt is what the chat model actually sees — producing more specific, domain-anchored answers from vague input.

A detailed technical write-up is in [`query-expansion-with-thesaurus.md`](query-expansion-with-thesaurus.md).

## How It Works

Each user turn goes through four stages:

```
Conversation history
        │
  1. Extract keywords ──► tokenize, resolve inflections ("dogs" → "dog"), filter by WordNet relations
        │
  2. Lookup relations ──► walk hyponym (~) and hypernym (@) edges in WordNet
        │
  3. Rank candidates  ──► score by gloss-context overlap + POS consistency + direct mention
        │
  4. LLM expansion    ──► feed top children + parents to LLM, rewrite the user prompt
        │
  Expanded prompt ──────► sent to main chat
```

**Children (hyponyms)** give specificity — `dog` → `working_dog`, `retriever`, `hound`.
**Parents (hypernyms)** anchor the domain — `dog` → `canine`, `domestic_animal`.

The ranking scores each candidate against the full conversation so far, which disambiguates word senses: in a conversation about dog breeds, `dog` the noun scores high while `dog` the verb is filtered out.

### Project structure

```
main.py                  CLI entry point, chat loop, expand_prompt()
wordnet/
  __init__.py            Data entities (8 dataclasses) + SQLite loader
  query.py               WordNetIndex — keyword extraction, hyponym/hypernym
                         lookup, relevance ranking
wordnet.db               Princeton WordNet 3.1 in SQLite (gitignored, ~70 MB)
```

## How to Run

### Prerequisites

- [uv](https://docs.astral.sh/uv/) package manager
- Python 3.14 (pinned in `.python-version`)
- [Ollama](https://ollama.com) running locally
- At least one Ollama model pulled (see below)
- `wordnet.db` in the project root (see below)

#### Ollama

Install and start Ollama following the [official guide](https://ollama.com). The app must be running before you start this project — `main()` checks connectivity on startup and exits if Ollama is unreachable.

#### Ollama model

Pull a model using the Ollama CLI. The default model is `exaone3.5:latest`:

```bash
ollama pull exaone3.5
```

You can use any model Ollama supports. For example:

```bash
ollama pull llama3.2
ollama pull gemma3
```

Then specify it via the `--model` flag or `OLLAMA_MODEL` env var (see Configuration below).

### Setup

```bash
# Install dependencies
uv sync

# Get wordnet.db — either build it or download it
# Option A: build from Princeton WordNet 3.1 data files
#   See https://github.com/chasangchual/wordnet-to-db
#   uv run main.py load --target sqlite
# Option B: download the pre-built db from the wordnet-to-db repo
curl -sL -o wordnet.db https://raw.githubusercontent.com/chasangchual/wordnet-to-db/main/wordnet.db

# Copy environment config (optional)
cp .env.example .env
# Edit .env to set OLLAMA_MODEL and OLLAMA_HOST if needed
```

### Run

```bash
# Default model (exaone3.5:latest)
uv run python main.py

# Override model
uv run python main.py --model llama3.2

# Override wordnet.db path
uv run python main.py --wordnet-db /path/to/wordnet.db
```

### Configuration

| Setting | CLI flag | Env var | Default |
|---------|----------|---------|---------|
| Ollama model | `--model` | `OLLAMA_MODEL` | `exaone3.5:latest` |
| Ollama host | — | `OLLAMA_HOST` | `http://localhost:11434` |
| WordNet DB path | `--wordnet-db` | — | `./wordnet.db` |

Precedence: CLI flag > env var > hardcoded default.
