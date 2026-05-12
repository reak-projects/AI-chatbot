from flask import Flask, request, jsonify, Response, send_from_directory
import os
import json
from datetime import datetime
from pathlib import Path
import openai

app = Flask(__name__, static_folder="static")

HISTORY_FILE = "chat_history.json"
MEMORY_FILE  = "memory.json"
MODEL_NAME   = "nvidia/nemotron-3-super-120b-a12b:free"

NO_MARKDOWN = "STRICT RULE: You must NEVER use any markdown. No asterisks, no stars, no bold, no headers, no bullet points, no dashes for lists. Write everything as plain conversational text only. If you want to make a list, use numbers like 1. 2. 3."
TEMPLATES = {
    "interview": f"Tu ek strict technical interviewer hai. Python, DSA, aur system design ke sawal pooch. {NO_MARKDOWN}",
    "chef":      f"Tu ek Indian chef hai. Sirf recipes aur cooking tips de. {NO_MARKDOWN}",
    "tutor":     f"Tu ek patient Python tutor hai. Simple language mein samjhao. {NO_MARKDOWN}",
    "fitness":   f"Tu ek fitness coach hai. Workout plans aur diet tips de. {NO_MARKDOWN}",
    "debug":     f"Tu ek senior software engineer hai. Code review karo aur bugs dhundo. {NO_MARKDOWN}",
}

FACT_KEYWORDS = [
    "kaun","kab","kitna","kitne","kya hai","kahan","who","when","where",
    "how many","what is","which","year","price","salary","population",
    "capital","founded","born","died","invented","released","percentage",
    "statistics","data","study","research","according"
]

def is_factual(text):
    return any(kw in text.lower() for kw in FACT_KEYWORDS)

def load_json(path):
    if Path(path).exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_client():
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise ValueError("OPENROUTER_API_KEY not set")
    return openai.OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")

def build_messages(history, system_prompt=None, memory=None):
    messages = []
    content = NO_MARKDOWN + "\n\n"
    if system_prompt:
        content += system_prompt + "\n\n"
    if memory:
        content += "What you remember about the user:\n"
        content += "\n".join(f"- {m}" for m in memory[-10:])
    messages.append({"role": "system", "content": content.strip()})
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    return messages

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data        = request.json
    user_msg    = data.get("message", "").strip()
    template    = data.get("template", None)
    system      = TEMPLATES.get(template) if template else data.get("system", None)

    history = load_json(HISTORY_FILE)
    memory  = load_json(MEMORY_FILE)

    history.append({"role": "user", "content": user_msg, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    client = get_client()

    def generate():
        full_reply = ""
        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=build_messages(history, system, memory),
                stream=True
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_reply_holder.append(delta)
                    yield f"data: {json.dumps({'token': delta})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        full = "".join(full_reply_holder).strip()
        history.append({"role": "assistant", "content": full, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_json(HISTORY_FILE, history)

        warn = is_factual(user_msg)
        yield f"data: {json.dumps({'done': True, 'warn': warn})}\n\n"

    full_reply_holder = []
    return Response(generate(), mimetype="text/event-stream")

@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(load_json(HISTORY_FILE))

@app.route("/api/history", methods=["DELETE"])
def clear_history():
    save_json(HISTORY_FILE, [])
    return jsonify({"ok": True})

@app.route("/api/memory", methods=["GET"])
def get_memory():
    return jsonify(load_json(MEMORY_FILE))

@app.route("/api/templates", methods=["GET"])
def get_templates():
    return jsonify(list(TEMPLATES.keys()))

if __name__ == "__main__":
    app.run(debug=True, port=8000)