#!/usr/bin/env python3
import os
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

try:
    import openai
except ImportError:
    print("Install karo: pip install openai")
    sys.exit(1)

HISTORY_FILE = "chat_history.json"
MODEL_NAME   = "nvidia/nemotron-3-super-120b-a12b:free"

# ── Colors ──────────────────────────────────────────────────────────────
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"
# ────────────────────────────────────────────────────────────────────────

def load_history():
    if Path(HISTORY_FILE).exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def format_for_api(history, system_prompt=None):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages += [{"role": msg["role"], "content": msg["content"]} for msg in history]
    return messages

def get_api_key():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("\n[!] OPENROUTER_API_KEY nahi mili.")
        print("    Free key lo: https://openrouter.ai")
        print("    Set karo: export OPENROUTER_API_KEY='your_key'\n")
        sys.exit(1)
    return key

def chat_loop(system_prompt=None):
    client = openai.OpenAI(
        api_key=get_api_key(),
        base_url="https://openrouter.ai/api/v1"
    )

    history = load_history()

    print(f"\n{BOLD}{CYAN}{'='*50}{RESET}")
    print(f"{BOLD}{CYAN}  🤖 CLI Chatbot  |  Model: {MODEL_NAME}{RESET}")
    if system_prompt:
        print(f"{YELLOW}  Role: {system_prompt[:60]}{'...' if len(system_prompt) > 60 else ''}{RESET}")
    print(f"{DIM}  Commands: quit | clear | history{RESET}")
    print(f"{BOLD}{CYAN}{'='*50}{RESET}\n")

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}You: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Bye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print(f"{DIM}Bye!{RESET}")
            break

        if user_input.lower() == "clear":
            history = []
            save_history(history)
            print(f"{YELLOW}[History cleared]{RESET}\n")
            continue

        if user_input.lower() == "history":
            if not history:
                print(f"{YELLOW}[No history yet]{RESET}\n")
            else:
                for i, msg in enumerate(history, 1):
                    if msg["role"] == "user":
                        print(f"{DIM}[{i}]{RESET} {GREEN}You:{RESET} {msg['content'][:80]}")
                    else:
                        print(f"{DIM}[{i}]{RESET} {CYAN}Bot:{RESET} {msg['content'][:80]}")
                print()
            continue

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.append({"role": "user", "content": user_input, "timestamp": timestamp})

        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=format_for_api(history, system_prompt),
                stream=True
            )
            print(f"\n{BOLD}{CYAN}Bot:{RESET} ", end="", flush=True)
            bot_reply = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
                    bot_reply += delta
            print("\n")
            bot_reply = bot_reply.strip()
        except Exception as e:
            print(f"\n{RED}[Error] {e}{RESET}\n")
            history.pop()
            continue

        history.append({"role": "assistant", "content": bot_reply, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_history(history)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI CLI Chatbot")
    parser.add_argument("--system", type=str, help="Chatbot ko role do", default=None)
    args = parser.parse_args()

    chat_loop(system_prompt=args.system)