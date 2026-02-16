import os
import uuid
import datetime
import subprocess
import webbrowser
import sqlite3
import logging
import psutil
import pyautogui
import pywhatkit
import urllib.parse
import time
import platform

from flask import Flask, request, jsonify, send_from_directory
from livekit import api
from groq import Groq

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KOKO_PRO")

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

# ================= CONFIG =================
LIVEKIT_API_KEY = ""
LIVEKIT_API_SECRET = ""
GROQ_API_KEY = ""

groq_client = Groq(api_key=GROQ_API_KEY)

# ================= DATABASE =================
def init_db():
    with sqlite3.connect("koko_memory.db") as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            bot_reply TEXT,
            timestamp DATETIME
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mem_key TEXT,
            mem_value TEXT,
            timestamp DATETIME
        )""")

def save_memory(u, b):
    with sqlite3.connect("koko_memory.db") as conn:
        conn.execute(
            "INSERT INTO chat_history (user_input, bot_reply, timestamp) VALUES (?, ?, ?)",
            (u, b, datetime.datetime.now())
        )

def save_user_memory(key, value):
    with sqlite3.connect("koko_memory.db") as conn:
        conn.execute(
            "INSERT INTO user_memory (mem_key, mem_value, timestamp) VALUES (?, ?, ?)",
            (key, value, datetime.datetime.now())
        )

def get_user_memory(key):
    with sqlite3.connect("koko_memory.db") as conn:
        row = conn.execute(
            "SELECT mem_value FROM user_memory WHERE mem_key=? ORDER BY id DESC LIMIT 1",
            (key,)
        ).fetchone()
        return row[0] if row else None

init_db()

# ================= SYSTEM INFO =================
def get_system_stats():
    cpu = psutil.cpu_percent()
    battery = psutil.sensors_battery()
    percent = battery.percent if battery else "N/A"
    return f"CPU {cpu}% | Battery {percent}%"

# ================= DEVICE CONTROL =================
def device_control(cmd):
    c = cmd.lower()

    if any(x in c for x in ["camera", "कैमरा", "cam", "selfie"]):
        subprocess.Popen("start microsoft.windows.camera:", shell=True)
        return "Camera opened"

    if any(x in c for x in ["notepad", "नोटपैड", "note likho"]):
        subprocess.Popen(["notepad"])
        return "Notepad opened"

    if any(x in c for x in ["वॉल्यूम बढ़ाओ", "increase volume"]):
        pyautogui.press("volumeup")
        return "Volume increased"

    if any(x in c for x in ["वॉल्यूम कम", "decrease volume"]):
        pyautogui.press("volumedown")
        return "Volume decreased"

    if "mute" in c or "म्यूट" in c:
        pyautogui.press("volumemute")
        return "Volume muted"


# --- SMART APP OPENING (ANY APP) ---
    # Example: "open calculator", "कैलकुलेटर खोलो"
    if "open" in c or "खोलो" in c or "launch" in c:
        words = c.split()
        # Try to find the app name (ignore open/launch/खोलो)
        skip_words = ["open", "launch", "खोलो", "koko", "please"]
        app_name = " ".join([w for w in words if w not in skip_words])
        if app_name:
            pyautogui.hotkey('win', 's')
            time.sleep(0.3)
            pyautogui.typewrite(app_name)
            time.sleep(0.3)
            pyautogui.press('enter')
            return f"{app_name.title()} opened"

    return None
# ================= YOUTUBE =================
def youtube_control(cmd):
    c = cmd.lower()
    yt_words = ["प्ले", "youtube", "सॉन्ग", "music", "गाना", "बजाओ", ]

    if any(w in c for w in yt_words):
        query = c
        for r in yt_words + ["koko", "please", "youtube par"]:
            query = query.replace(r, "")
        query = query.strip()

        if query:
            pywhatkit.playonyt(query)
            time.sleep(6)
            pyautogui.press("f")
            return f"Playing Song {query}"

    return None

# ================= REMEMBER LOGIC =================
def remember_logic(cmd):
    c = cmd.lower()

    # Name save
    if any(x in c for x in ["yaad rakh", "remember", "याद रखना"]):
        if "mera naam" in c:
            name = c.split("mera naam")[-1].replace("hai","").replace("है","").replace("hoon","").replace(" हूँ","").strip().title()
            save_user_memory("name", name)
            return f"ठीक है, आपका नाम {name} याद रख लिया"

        save_user_memory("note", c)
        return "ठीक है, ये बात याद रख ली"

    # Name retrieval
    if any(x in c for x in ["मेरा नाम क्या है", "my name"]):
        name = get_user_memory("name")
        return f"आपका नाम {name} है" if name else "kaushal"

    return None

# ================= IDENTITY LOGIC =================
def identity_logic(cmd):
    c = cmd.lower()

    if any(x in c for x in ["तुमको किसने बनाया", "who created you"]):
        return "मुझे ko Kaushal ne banaya hai"

    if any(x in c for x in ["tum kon ho", "who are you"]):
        return "Main Kaushal ki personal AI hoon"

    if any(x in c for x in ["तुमको कब बनाया", "when were you created"]):
        return "मुझे जनवरी २०२६ में बनाया गया था"

    return None

# ================= AI (SMART ANSWERS / ADVICE MODE) =================
def get_ai_response(user_input):
    try:
        # Fetch stored user name if any
        user_name = get_user_memory("name") 

        # System prompt guides AI to give detailed answers for advice
        system_prompt = f"""
You are KOKO AI, a smart personal assistant.

RULES:
- Fact-based question (like 'Who is CM of Delhi?') → first give direct answer, then 2-3 line short explanation.
- Life/advice questions (like relationship, personal problems) → reply in detailed and helpful manner, giving examples or steps.
- Hindi/Hinglish → reply in Hindi, English → reply in English.
- Personalize replies using user's name: {user_name}
- Keep tone friendly, supportive, and informative.
"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5  # more creativity for advice
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(e)
        return "⚠️ Sorry, I am offline right now but still listening."


# ================= ROUTES =================
@app.route("/process_command", methods=["POST"])
def process_command():
    user_cmd = request.json.get("command", "").strip()

    for handler in (remember_logic, identity_logic, device_control, youtube_control):
        reply = handler(user_cmd)
        if reply:
            save_memory(user_cmd, reply)
            return jsonify({"reply": reply})

    reply = get_ai_response(user_cmd)
    if not reply:
        reply = "⚠️ Offline mode active. Main system commands samajh rahi hoon."

    save_memory(user_cmd, reply)
    return jsonify({"reply": reply})

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# ================= MAIN =================
if __name__ == "__main__":
    print("\n💠 KOKO PRO ONLINE | ADVANCED MODE READY")
    print("🌐 http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)

