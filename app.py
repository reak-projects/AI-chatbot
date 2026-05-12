#!/usr/bin/env python3
import os
import json
import sys
import argparse
import re
from datetime import datetime
from pathlib import Path

try:
    import openai
except ImportError:
    print("Install karo: pip install openai")
    sys.exit(1)

HISTORY_FILE  = "chat_history.json"
MEMORY_FILE   = "memory.json"
MODEL_NAME    = "nvidia/nemotron-3-super-120b-a12b:free"

# ── Colors ──────────────────────────────────────────────────────────────
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"
# ────────────────────────────────────────────────────────────────────────

NO_MARKDOWN = "Never use markdown formatting. No **, no *, no #, no --, no bullet dashes. Use plain text only. Use numbers for lists."

# ── Hallucination trigger keywords ──────────────────────────────────────
FACT_KEYWORDS = [
    "kaun", "kab", "kitna", "kitne", "kya hai", "kahan", "kon sa",
    "who", "when", "where", "how many", "what is", "which", "year",
    "price", "salary", "population", "capital", "founded", "born",
    "died", "invented", "discovered", "released", "version",
    "percentage", "statistics", "data", "study", "research", "according"
]

def is_factual(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in FACT_KEYWORDS)
# ────────────────────────────────────────────────────────────────────────

# ── Prompt Templates ────────────────────────────────────────────────────
TEMPLATES = {
    "interview": f"Tu ek strict technical interviewer hai. User ko Python, DSA, aur system design ke sawal pooch. Ek ek sawal pooch, answer ke baad feedback de. {NO_MARKDOWN}",
    "chef":      f"Tu ek Indian chef hai. Sirf recipes aur cooking tips de. Ingredients aur steps clearly batao. {NO_MARKDOWN}",
    "tutor":     f"Tu ek patient Python tutor hai. Simple language mein samjhao, examples do, aur mistakes gently correct karo. {NO_MARKDOWN}",
    "fitness":   f"Tu ek fitness coach hai. Workout plans, diet tips, aur motivation de. Safe aur realistic advice do. {NO_MARKDOWN}",
    "debug":     f"Tu ek senior software engineer hai. User ka code review karo, bugs dhundo, aur better solutions suggest karo. {NO_MARKDOWN}",
}
# ────────────────────────────────────────────────────────────────────────

def load_history():
    if Path(HISTORY_FILE).exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_memory():
    if Path(MEMORY_FILE).exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def extract_memory(client, conversation):
    if len(conversation) < 4:
        return None
    recent = conversation[-6:]
    convo_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{
                "role": "user",
                "content": f"""From this conversation, extract only important facts about the user (name, profession, preferences, goals). 
Return a single short sentence or null if nothing important.
Do not include generic info.

Conversation:
{convo_text}

Reply with only the fact or the word null."""
            }],
            stream=False
        )
        fact = response.choices[0].message.content.strip()
        if fact.lower() != "null" and len(fact) > 5:
            return fact
    except:
        pass
    return None

def format_for_api(history, system_prompt=None, memory=None):
    messages = []
    system_content = NO_MARKDOWN + "\n\n"
    if system_prompt:
        system_content += system_prompt + "\n\n"
    if memory:
        system_content += "What you remember about the user:\n"
        system_content += "\n".join(f"- {m}" for m in memory[-10:])
    messages.append({"role": "system", "content": system_content.strip()})
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

def chat_loop(system_prompt=None, template=None):
    client = openai.OpenAI(
        api_key=get_api_key(),
        base_url="https://openrouter.ai/api/v1"
    )

    if template:
        if template not in TEMPLATES:
            print(f"{RED}Template '{template}' nahi mila.{RESET}")
            print(f"{YELLOW}Available templates: {', '.join(TEMPLATES.keys())}{RESET}")
            sys.exit(1)
        system_prompt = TEMPLATES[template]

    history = load_history()
    memory  = load_memory()

    print(f"\n{BOLD}{CYAN}{'='*50}{RESET}")
    print(f"{BOLD}{CYAN}  🤖 CLI Chatbot  |  Model: {MODEL_NAME}{RESET}")
    if template:
        print(f"{YELLOW}  Template: {template}{RESET}")
    elif system_prompt:
        print(f"{YELLOW}  Role: {system_prompt[:60]}{'...' if len(system_prompt) > 60 else ''}{RESET}")
    if memory:
        print(f"{DIM}  Memory: {len(memory)} facts loaded{RESET}")
    print(f"{DIM}  Commands: quit | clear | history | memory | templates{RESET}")
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

        if user_input.lower() == "templates":
            print(f"{YELLOW}Available templates:{RESET}")
            for name, prompt in TEMPLATES.items():
                print(f"  {BOLD}{name}{RESET} — {prompt[:60]}...")
            print(f"\n{DIM}Use: python3 app.py --template <name>{RESET}\n")
            continue

        if user_input.lower() == "memory":
            if not memory:
                print(f"{YELLOW}[No memory yet]{RESET}\n")
            else:
                print(f"{YELLOW}Remembered facts:{RESET}")
                for i, fact in enumerate(memory, 1):
                    print(f"  {DIM}[{i}]{RESET} {fact}")
                print()
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
                messages=format_for_api(history, system_prompt, memory),
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

        # ── Hallucination warning ────────────────────────────────────
        if is_factual(user_input):
            print(f"{YELLOW}[!] Yeh response factual information contain kar sakta hai — important cheezein verify karo.{RESET}\n")
        # ────────────────────────────────────────────────────────────

        history.append({"role": "assistant", "content": bot_reply, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_history(history)

        if len(history) % 4 == 0:
            fact = extract_memory(client, history)
            if fact and fact not in memory:
                memory.append(fact)
                save_memory(memory)
                print(f"{DIM}[Memory saved: {fact[:60]}]{RESET}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI CLI Chatbot")
    parser.add_argument("--system",   type=str, help="Custom role do chatbot ko", default=None)
    parser.add_argument("--template", type=str, help="Template use karo (interview/chef/tutor/fitness/debug)", default=None)
    args = parser.parse_args()

    chat_loop(system_prompt=args.system, template=args.template)