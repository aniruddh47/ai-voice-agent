import os
import json
import queue
import asyncio
import sounddevice as sd
import numpy as np
import time

from vosk import Model, KaldiRecognizer
from dotenv import load_dotenv

import google.generativeai as genai

from edge_tts import Communicate
from playsound import playsound





MODEL_PATH = "vosk-model-small-en-in-0.4"
VOICE_FILE = "response.mp3"

SAMPLE_RATE = 16000
CHUNK_SIZE = 4000


# ==========================================================
# LOAD ENV
# ==========================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise Exception("GEMINI_API_KEY missing")


# ==========================================================
# NEW GEMINI CLIENT
# ==========================================================

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


# ==========================================================
# LOAD COLLEGE INFO
# ==========================================================

with open("college_info.json", "r", encoding="utf-8") as f:
    COLLEGE_INFO = json.load(f)


# ==========================================================
# BUILD PROMPT
# ==========================================================

def build_prompt(user_text):

    admissions = COLLEGE_INFO.get("admissions", {})

    fees = {}

    for course, info in COLLEGE_INFO.get("courses", {}).get("undergraduate", {}).items():
        fees[course] = info.get("fees")

    for course, info in COLLEGE_INFO.get("courses", {}).get("postgraduate", {}).items():
        fees[course] = info.get("fees")

    prompt = f"""
You are a friendly admission counselor of {COLLEGE_INFO.get('college_name')}.

Rules:
- Reply naturally like human
- Maximum 2 sentences
- Short and clear answer

Data:
Admission start: {admissions.get('start_date')}
Last date: {admissions.get('last_date')}
Eligibility: {admissions.get('eligibility')}
Fees: {fees}
Placements: {COLLEGE_INFO.get('placements')}
Hostel: {COLLEGE_INFO.get('hostel')}

Parent question:
{user_text}
"""

    return prompt


# ==========================================================
# AI RESPONSE
# ==========================================================

def get_ai_response(text):

    try:

        prompt = build_prompt(text)

        response = model.generate_content(prompt)
        reply = response.text.strip()
        if reply == "":
            reply = "Please repeat."
        return reply

    except Exception as e:

        print("AI Error:", e)

        return "Sorry, please try again."


# ==========================================================
# TTS
# ==========================================================

async def speak(text):

    try:

        communicate = Communicate(text, "en-IN-NeerjaNeural")

        await communicate.save(VOICE_FILE)

        playsound(VOICE_FILE)

    except Exception as e:

        print("TTS error:", e)

    finally:

        time.sleep(0.5)  # Wait for playsound to release the file
        
        if os.path.exists(VOICE_FILE):
            try:
                os.remove(VOICE_FILE)
            except PermissionError:
                pass  # File still in use, skip deletion


# ==========================================================
# VOSK
# ==========================================================

if not os.path.exists(MODEL_PATH):
    raise Exception("Download VOSK model")

vosk_model = Model(MODEL_PATH)

recognizer = KaldiRecognizer(vosk_model, SAMPLE_RATE)

q = queue.Queue()


def callback(indata, frames, time_info, status):

    if status:
        print(status)

    q.put(bytes(indata))


def clear_queue():

    while not q.empty():
        q.get()


# ==========================================================
# MAIN
# ==========================================================

def main():

    global recognizer

    print("\n🎓 Admission Counselor Started")
    print("🎤 Speak now...\n")

    stream = sd.InputStream(

        samplerate=SAMPLE_RATE,
        blocksize=CHUNK_SIZE,
        dtype="int16",
        channels=1,
        callback=callback

    )

    stream.start()

    while True:

        try:

            data = q.get()

            if recognizer.AcceptWaveform(data):

                result = json.loads(recognizer.Result())

                text = result.get("text", "").strip()

                if text == "":
                    continue

                print("Parent:", text)

                if text.lower() == "stop":
                    break

                stream.stop()

                print("Thinking...")

                reply = get_ai_response(text)

                print("Counselor:", reply)

                asyncio.run(speak(reply))

                recognizer = KaldiRecognizer(vosk_model, SAMPLE_RATE)

                clear_queue()

                stream.start()

        except KeyboardInterrupt:
            break

    stream.stop()
    stream.close()


# ==========================================================
# ENTRY
# ==========================================================

if __name__ == "__main__":

    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    main()
