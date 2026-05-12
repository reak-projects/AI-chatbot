#!/usr/bin/env python3
import os
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import openai
except ImportError:
    print("Install karo: pip install openai")
    sys.exit(1)

HISTORY_FILE = "chat_history.json"
MODEL_NAME   = "nvidia/nemotron-3-super-120b-a12b:free"

def load_history():
    if Path(HISTORY_FILE).exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def format_for_api(history):
    return [{"role": msg["role"], "content": msg["content"]} for msg in history]

def get_api_key():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("\n[!] OPENROUTER_API_KEY nahi mili.")
        print("    Free key lo: https://openrouter.ai")
        print("    Set karo: export OPENROUTER_API_KEY='your_key'\n")
        sys.exit(1)
    return key

def chat_loop():
    client = openai.OpenAI(
        api_key=get_api_key(),
        base_url="https://openrouter.ai/api/v1"
    )

    history = load_history()

    print(f"\n{'='*50}")
    print(f"  CLI Chatbot  |  Model: {MODEL_NAME}")
    print(f"  Commands: quit | clear | history")
    print(f"{'='*50}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("Bye!")
            break

        if user_input.lower() == "clear":
            history = []
            save_history(history)
            print("[History cleared]\n")
            continue

        if user_input.lower() == "history":
            if not history:
                print("[No history yet]\n")
            else:
                for i, msg in enumerate(history, 1):
                    role = "You" if msg["role"] == "user" else "Bot"
                    print(f"[{i}] {role}: {msg['content'][:80]}")
                print()
            continue

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.append({"role": "user", "content": user_input, "timestamp": timestamp})

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=format_for_api(history)
            )
            bot_reply = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"\n[Error] {e}\n")
            history.pop()
            continue

        history.append({"role": "assistant", "content": bot_reply, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_history(history)
        print(f"\nBot: {bot_reply}\n")

if __name__ == "__main__":
    chat_loop()