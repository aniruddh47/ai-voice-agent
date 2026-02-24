# ==========================================================
# FINAL YEAR PROJECT
# AI ADMISSION COUNSELOR (WHISPER + HYBRID ARCHITECTURE)
# Optimized for 8GB RAM
# ==========================================================

import os
import json
import time
import re
from datetime import datetime

import sounddevice as sd
import numpy as np
import whisper
import pyttsx3

from dotenv import load_dotenv
from google import genai
from google.genai import types
from langdetect import detect


# ==========================================================
# CONFIG
# ==========================================================

SAMPLE_RATE = 16000
RECORD_SECONDS = 5  # adjustable

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise Exception("Add GEMINI_API_KEY in .env")

client = genai.Client(api_key=API_KEY)

print("Loading Whisper model (base)...")
whisper_model = whisper.load_model("base")  # Best for 8GB RAM


# ==========================================================
# LANGUAGE SETTINGS
# ==========================================================

VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "mr": "mr-IN-AarohiNeural",
}


def detect_language(text):
    try:
        lang = detect(text)
        return lang if lang in ["en", "hi", "mr"] else "en"
    except:
        return "en"


# ==========================================================
# SMART KNOWLEDGE BASE
# ==========================================================

class SmartKnowledgeBase:

    def __init__(self):
        with open("admission_procedures.json", "r", encoding="utf-8") as f:
            self.admission = json.load(f)

        with open("departments_info.json", "r", encoding="utf-8") as f:
            self.departments = json.load(f)

        with open("facilities_detailed.json", "r", encoding="utf-8") as f:
            self.facilities = json.load(f)

    def search(self, query):
        q = query.lower()

        if "jee" in q:
            return "We accept JEE Main with 45 percentile."
        if "cat" in q:
            return "MBA accepts CAT with 50 percentile followed by GD and PI."
        if "hostel fees" in q:
            return "Hostel total first year cost is 1,15,000 including mess."
        if "library" in q:
            return "Central library has 50,000 books and digital access."
        if "cse" in q:
            return "CSE offers AI, ML, Cloud and Cyber Security specializations."

        return None


kb = SmartKnowledgeBase()


# ==========================================================
# LEAD CAPTURE
# ==========================================================

user_info = {}


def extract_user_info(text):
    phone = re.search(r"[6-9]\d{9}", text)
    if phone:
        user_info["phone"] = phone.group()

    email = re.search(r"\S+@\S+\.\S+", text)
    if email:
        user_info["email"] = email.group()


def save_lead():
    if not user_info:
        return

    leads = []
    if os.path.exists("leads.json"):
        with open("leads.json", "r") as f:
            leads = json.load(f)

    leads.append({
        "info": user_info,
        "timestamp": datetime.now().isoformat()
    })

    with open("leads.json", "w") as f:
        json.dump(leads, f, indent=2)

    print("Lead saved.")


# ==========================================================
# AUDIO RECORDING (WHISPER)
# ==========================================================

def record_audio():
    print("Speak now...")
    recording = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
                       samplerate=SAMPLE_RATE,
                       channels=1,
                       dtype="float32")
    sd.wait()
    return recording


def transcribe_audio(audio):
    # Flatten to 1D and pass directly as numpy array (no ffmpeg needed)
    audio_flat = audio.flatten()
    result = whisper_model.transcribe(audio_flat, fp16=False)
    return result["text"].strip()


# ==========================================================
# GEMINI PROMPT
# ==========================================================

def build_prompt(user_text, lang):

    language_instruction = {
        "en": "Reply in English.",
        "hi": "Reply in Hindi mixed with English.",
        "mr": "Reply in Marathi mixed with English."
    }

    prompt = f"""
You are a friendly admission counselor.

Rules:
- Maximum 2 sentences
- Under 30 words
- Sound natural

{language_instruction.get(lang)}

Student question:
{user_text}

Answer:
"""
    return prompt.strip()


def get_ai_response(text):

    lang = detect_language(text)

    # JSON first
    json_answer = kb.search(text)
    if json_answer:
        return json_answer, lang

    extract_user_info(text)

    try:
        prompt = build_prompt(text, lang)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                max_output_tokens=60,
            ),
        )

        reply = response.text
        if not reply or reply.strip() == "":
            return "Please repeat.", lang
        return reply.strip(), lang

    except Exception as e:
        print("API Error:", e)
        return "Please repeat.", lang


# ==========================================================
# TEXT TO SPEECH (OFFLINE - pyttsx3)
# ==========================================================

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 160)
tts_engine.setProperty('volume', 1.0)

# Try to set an Indian English female voice if available
for voice in tts_engine.getProperty('voices'):
    if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
        tts_engine.setProperty('voice', voice.id)
        break


def speak(text, lang="en"):
    try:
        print("[TTS] Speaking:", text)
        tts_engine.say(text)
        tts_engine.runAndWait()
        print("[TTS] Done")
    except Exception as e:
        print("TTS Error:", e)


# ==========================================================
# MAIN LOOP
# ==========================================================

def main():

    print("\n🎓 AI Admission Counselor Started (Whisper Mode)")
    print("Say 'stop' to exit\n")

    greeting = "Hello! How can I help you with admissions today?"
    print("Counselor:", greeting)
    speak(greeting)

    while True:

        audio = record_audio()
        text = transcribe_audio(audio)

        if not text:
            continue

        print("You:", text)

        if text.lower() in ["stop", "exit"]:
            farewell = "Thank you for contacting us."
            print("Counselor:", farewell)
            speak(farewell)
            save_lead()
            break

        print("Thinking...")

        reply, lang = get_ai_response(text)

        print(f"Counselor ({lang}):", reply)

        speak(reply, lang)


# ==========================================================
# ENTRY
# ==========================================================

if __name__ == "__main__":
    main()