import argparse
import sys

from dotenv import load_dotenv
from ollama import Client

load_dotenv()

DEFAULT_MODEL = "exaone3.5:latest"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ollama chat CLI")
    parser.add_argument(
        "--model", default=None, help="Ollama model to use (overrides OLLAMA_MODEL env)"
    )
    return parser.parse_args()


def resolve_model(arg_model: str | None) -> str:
    import os

    return arg_model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)


def chat_loop(client: Client, model: str) -> None:
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

        messages.append({"role": "user", "content": user_input})

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

        messages.append({"role": "assistant", "content": "".join(assistant_chunks)})

    print("Session ended.")


def main() -> None:
    args = parse_args()
    model = resolve_model(args.model)

    host = __import__("os").environ.get("OLLAMA_HOST")
    client = Client(host=host) if host else Client()

    try:
        client.list()
    except Exception as e:
        print(f"Cannot connect to Ollama: {e}", file=sys.stderr)
        sys.exit(1)

    chat_loop(client, model)


if __name__ == "__main__":
    main()
