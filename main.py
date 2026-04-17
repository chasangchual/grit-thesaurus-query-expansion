import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from ollama import Client

from wordnet import WordNetData, load_wordnet_db
from wordnet.query import WordNetIndex

load_dotenv()

DEFAULT_MODEL = "exaone3.5:latest"
DEFAULT_WORDNET_DB = Path(__file__).parent / "wordnet.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ollama chat CLI")
    parser.add_argument(
        "--model", default=None, help="Ollama model to use (overrides OLLAMA_MODEL env)"
    )
    parser.add_argument(
        "--wordnet-db",
        default=None,
        help="Path to wordnet.db (overrides default location)",
    )
    return parser.parse_args()


def resolve_model(arg_model: str | None) -> str:
    import os

    return arg_model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)


def expand_prompt(
    client: Client, model: str, user_input: str, children: list, parents: list
) -> str:
    if not children and not parents:
        return user_input
    parts = []
    if children:
        parts.append("Related specific words (children/hyponyms):")
        parts.extend(f"- {c.lemma} ({c.pos}): {c.gloss}" for c in children)
    if parents:
        parts.append("Related broader words (parents/hypernyms):")
        parts.extend(f"- {p.lemma} ({p.pos}): {p.gloss}" for p in parents)
    candidates = "\n".join(parts)
    expand_msg = {
        "role": "user",
        "content": (
            f"Rewrite the following user message to naturally incorporate the most relevant "
            f"related words from the list below. Only use words that genuinely fit the meaning "
            f"— do not force words that don't belong. Keep the expanded message concise and "
            f"natural. Output ONLY the rewritten message, nothing else.\n\n"
            f"User message: {user_input}\n\n"
            f"{candidates}"
        ),
    }
    try:
        resp = client.chat(model=model, messages=[expand_msg])
        expanded = (resp.message.content or "").strip()
        if expanded and len(expanded) < len(user_input) * 5:
            return expanded
    except Exception:
        pass
    return user_input


def chat_loop(client: Client, model: str, wn: WordNetIndex) -> None:
    messages: list[dict] = []
    print(f"Chatting with {model} — type /quit or /exit to stop, Ctrl+C also works\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except KeyboardInterrupt, EOFError:
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit"):
            break

        children, parents = wn.top_related(messages) if messages else ([], [])
        expanded = expand_prompt(client, model, user_input, children, parents)
        if expanded != user_input:
            print(f"Expanded> {expanded}\n")

        messages.append({"role": "user", "content": expanded})

        print(f"{model}> ", end="", flush=True)
        assistant_chunks: list[str] = []

        try:
            stream = client.chat(model=model, messages=messages, stream=True)
            for chunk in stream:
                content = chunk.message.content or ""
                print(content, end="", flush=True)
                assistant_chunks.append(content)
            print("\n")
        except Exception as e:
            print(f"\nError: {e}\n")
            messages.pop()
            continue

        assistant_text = "".join(assistant_chunks)
        messages.append({"role": "assistant", "content": assistant_text})

        children, parents = wn.top_related(messages)
        if children or parents:
            print("Related words:")
            for c in children:
                print(f"  ↓ {c.lemma} ({c.pos}) — {c.gloss}")
            for p in parents:
                print(f"  ↑ {p.lemma} ({p.pos}) — {p.gloss}")
            print()


def main() -> None:
    args = parse_args()
    model = resolve_model(args.model)

    db_path = Path(args.wordnet_db) if args.wordnet_db else DEFAULT_WORDNET_DB
    if not db_path.exists():
        print(f"wordnet.db not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading WordNet from {db_path} …")
    wordnet_data: WordNetData = load_wordnet_db(db_path)
    print(
        f"Loaded {len(wordnet_data.words)} words, "
        f"{len(wordnet_data.synsets)} synsets, "
        f"{len(wordnet_data.senses)} senses, "
        f"{len(wordnet_data.semantic_relations)} semantic relations"
    )

    print("Building WordNet index …")
    wn_index = WordNetIndex(wordnet_data)

    host = __import__("os").environ.get("OLLAMA_HOST")
    client = Client(host=host) if host else Client()

    try:
        client.list()
    except Exception as e:
        print(f"Cannot connect to Ollama: {e}", file=sys.stderr)
        sys.exit(1)

    chat_loop(client, model, wn_index)


if __name__ == "__main__":
    main()
