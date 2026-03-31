import os
import json
import time
import asyncio
import speech_recognition as sr
from faster_whisper import WhisperModel
from edge_tts import Communicate
from playsound import playsound
from dotenv import load_dotenv
from google import genai
import difflib

question_cache = {}
conversation_history = []

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

load_dotenv()

WHISPER_MODEL_SIZE = "small.en"
AUDIO_INPUT_FILE = "temp_input.wav"
AUDIO_OUTPUT_FILE = "response.mp3"
TTS_VOICE = "en-IN-NeerjaNeural"
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")
LISTEN_TIMEOUT_SEC = float(os.getenv("LISTEN_TIMEOUT_SEC", "8"))
PHRASE_TIME_LIMIT_SEC = float(os.getenv("PHRASE_TIME_LIMIT_SEC", "12"))
AMBIENT_CALIBRATION_SEC = float(os.getenv("AMBIENT_CALIBRATION_SEC", "1.0"))
MIC_DEVICE_INDEX = os.getenv("MIC_DEVICE_INDEX")
MIC_DEVICE_INDEX = int(MIC_DEVICE_INDEX) if MIC_DEVICE_INDEX and MIC_DEVICE_INDEX.isdigit() else None

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise Exception("GEMINI_API_KEY missing from environment variables.")

client = genai.Client(api_key=API_KEY)

print("⏳ Loading Faster-Whisper Model...")
stt_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.5


def print_microphone_diagnostics():
    try:
        names = sr.Microphone.list_microphone_names()
        if not names:
            print("⚠️  No microphone devices detected.")
            return
        print("🎙️  Available microphones:")
        for idx, name in enumerate(names):
            marker = " <- selected" if MIC_DEVICE_INDEX == idx else ""
            print(f"  [{idx}] {name}{marker}")
        if MIC_DEVICE_INDEX is not None and MIC_DEVICE_INDEX >= len(names):
            print("⚠️  MIC_DEVICE_INDEX is out of range. Falling back to system default microphone.")
    except Exception as e:
        print(f"⚠️  Could not list microphones: {e}")


# ── NEW: Load all JSON files at startup ──────────────────────────────────────
def load_all_college_data():
    """Merges all JSON data files into one dictionary at startup."""
    data = {}
    json_files = [
        "college_info.json",
        "facilities_detailed.json",
        "departments_info.json",
        "admission_procedures.json"
    ]
    for fname in json_files:
        file_path = os.path.join(DATA_DIR, fname)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data.update(json.load(f))
                except json.JSONDecodeError as e:
                    print(f"⚠️  Could not parse {file_path}: {e}")
        else:
            print(f"⚠️  File not found: {file_path}")
    return data

COLLEGE_DATA = load_all_college_data()  # Loaded ONCE at startup


# ── FIXED: build_prompt now reads from the merged COLLEGE_DATA ───────────────
def build_prompt(user_text):
    text = user_text.lower()

    # Pull top-level info that exists in your actual JSON structure
    overview      = COLLEGE_DATA.get("university_overview", {})
    college_name  = overview.get("about", "Sanjay Ghodawat University, Kolhapur")
    admissions    = COLLEGE_DATA.get("admissions", {})
    departments   = COLLEGE_DATA.get("departments", {})          # from college_info.json
    dept_detail   = COLLEGE_DATA.get("departments", {})          # from departments.json (same key, merged)
    placements    = COLLEGE_DATA.get("career_and_placements", {})
    campus_life   = COLLEGE_DATA.get("campus_life", {})
    hostel_detail = COLLEGE_DATA.get("hostel_detailed", {})
    transport     = COLLEGE_DATA.get("transport_detailed", {})
    sports        = COLLEGE_DATA.get("sports_facilities_detailed", {})
    library       = COLLEGE_DATA.get("library_detailed", {})
    canteen       = COLLEGE_DATA.get("canteen_facilities", {})
    wifi          = COLLEGE_DATA.get("wifi_internet", {})
    medical       = COLLEGE_DATA.get("medical_facilities", {})
    admission_proc = COLLEGE_DATA.get("admission_procedures_detailed", {})

    prompt = f"""You are a polite and professional admission counselor for Sanjay Ghodawat University (SGU), Kolhapur.
You are speaking on a phone call with a parent or prospective student.

CRITICAL RULES:
- Keep your answer short (maximum 2-3 sentences).
- Speak naturally and conversationally, like a real phone call.
- NEVER use special formatting like *, #, or bullet points.
- NEVER say "None" or "I don't have that information" — use the data provided below.
- Always sound warm, confident, and helpful.

"""

    prompt += "=== RELEVANT COLLEGE DATA ===\n"

    # General / overview — always included
    prompt += f"COLLEGE: {overview}\n"

    # Courses / departments
    if any(word in text for word in [
        "course", "program", "branch", "department", "btech", "b.tech",
        "mba", "mca", "bca", "m.tech", "engineering", "cse", "aiml",
        "computer", "mechanical", "civil", "electronics", "what do you teach",
        "subjects", "curriculum", "specialization"
    ]):
        prompt += f"\nCOURSES & DEPARTMENTS (summary): {COLLEGE_DATA.get('departments', {})}\n"
        # Also pull the detailed dept info if available
        btech_sw  = COLLEGE_DATA.get("departments", {}).get("btech_software", {})
        btech_core = COLLEGE_DATA.get("departments", {}).get("btech_core", {})
        prompt += f"B.Tech Software (AIML/CSE): {btech_sw}\n"
        prompt += f"B.Tech Core (Civil/Mech/Aero): {btech_core}\n"

    # Admissions & eligibility
    if any(word in text for word in [
        "admission", "apply", "eligibility", "process", "exam", "document",
        "date", "when", "how to join", "entrance", "jee", "cet", "counseling",
        "fee", "fees", "scholarship", "reservation", "quota"
    ]):
        prompt += f"\nADMISSIONS: {admissions}\n"
        prompt += f"\nADMISSION PROCEDURES (detailed): {admission_proc}\n"

    # Placements
    if any(word in text for word in [
        "placement", "salary", "package", "company", "recruit", "job",
        "lpa", "offer", "campus", "hire", "career"
    ]):
        prompt += f"\nPLACEMENTS: {placements}\n"

    # Hostel & accommodation
    if any(word in text for word in [
        "hostel", "stay", "accommodation", "room", "warden", "mess",
        "boys", "girls", "food", "living", "resident"
    ]):
        prompt += f"\nHOSTEL (summary): {campus_life.get('hostel', '')}\n"
        prompt += f"\nHOSTEL (detailed): {hostel_detail}\n"

    # Transport
    if any(word in text for word in [
        "bus", "transport", "pickup", "drop", "route", "sangli",
        "ichalkaranji", "travel", "commute"
    ]):
        prompt += f"\nTRANSPORT: {transport}\n"

    # Sports & facilities
    if any(word in text for word in [
        "sport", "cricket", "football", "gym", "ground", "court",
        "badminton", "athletics", "facility", "facilities"
    ]):
        prompt += f"\nSPORTS: {sports}\n"

    # Library
    if any(word in text for word in [
        "library", "book", "read", "study", "journal", "e-book", "digital"
    ]):
        prompt += f"\nLIBRARY: {library}\n"

    # Canteen & food
    if any(word in text for word in [
        "canteen", "food", "eat", "cafe", "snack", "juice", "veg", "menu"
    ]):
        prompt += f"\nCANTEEN: {canteen}\n"

    # WiFi & internet
    if any(word in text for word in ["wifi", "internet", "network", "speed", "connection"]):
        prompt += f"\nWIFI: {wifi}\n"

    # Medical
    if any(word in text for word in ["medical", "doctor", "health", "clinic", "hospital", "ambulance", "sick"]):
        prompt += f"\nMEDICAL: {medical}\n"

    # FALLBACK — if nothing matched, send the full overview + placements
    has_specific_data = any(keyword in prompt for keyword in [
        "COURSES", "ADMISSIONS", "PLACEMENTS", "HOSTEL", "TRANSPORT",
        "SPORTS", "LIBRARY", "CANTEEN", "WIFI", "MEDICAL"
    ])
    if not has_specific_data:
        prompt += f"\nGENERAL INFO: {overview}\n"
        prompt += f"\nPLACEMENTS: {placements}\n"
        prompt += f"\nCAMPUS LIFE: {campus_life}\n"

    prompt += f"\n=== PARENT'S QUESTION ===\n{user_text}\n"
    prompt += "\nAnswer the question naturally in 2-3 sentences using the data above. Do NOT say None."

    return prompt


# ── Rest of your code unchanged ──────────────────────────────────────────────
def listen_and_transcribe():
    try:
        with sr.Microphone(device_index=MIC_DEVICE_INDEX) as source:
            print("\n🎤 Listening... (Speak now)")
            recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_CALIBRATION_SEC)
            audio = recognizer.listen(
                source,
                timeout=LISTEN_TIMEOUT_SEC,
                phrase_time_limit=PHRASE_TIME_LIMIT_SEC,
            )
            with open(AUDIO_INPUT_FILE, "wb") as f:
                f.write(audio.get_wav_data())
    except sr.WaitTimeoutError:
        print("⌛ No speech detected within timeout window. Please speak a little louder and closer to the mic.")
        return ""
    except Exception as e:
        print(f"❌ Microphone error: {e}")
        return ""

    if not os.path.exists(AUDIO_INPUT_FILE) or os.path.getsize(AUDIO_INPUT_FILE) == 0:
        print("⚠️  Captured audio file is empty.")
        return ""

    print("⏳ Transcribing...")
    segments, _ = stt_model.transcribe(
        AUDIO_INPUT_FILE,
        beam_size=5,
        language=WHISPER_LANGUAGE,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    text = " ".join([seg.text for seg in segments]).strip()
    if not text:
        print("⚠️  Speech was captured but transcription is empty. Try reducing background noise or changing mic device.")
    return text


def get_ai_response(text):
    user_query = text.lower().strip()
    similar = difflib.get_close_matches(user_query, question_cache.keys(), n=1, cutoff=0.80)
    if similar:
        print("⚡ [CACHE HIT]")
        return question_cache[similar[0]]
    try:
        prompt = build_prompt(text)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        reply = response.text.strip()
        if reply:
            question_cache[user_query] = reply
            return reply
        return "I didn't quite catch that. Could you repeat?"
    except Exception as e:
        print(f"AI Error: {e}")
        return "I'm having trouble connecting right now. Give me a moment."


async def speak_async(text):
    print(f"Counselor: {text}")
    clean_text = text.replace("*", "").replace("#", "")
    try:
        communicate = Communicate(clean_text, TTS_VOICE)
        await communicate.save(AUDIO_OUTPUT_FILE)
        playsound(AUDIO_OUTPUT_FILE)
    except Exception as e:
        print(f"❌ [TTS Error]: {e}")
    finally:
        time.sleep(0.5)
        if os.path.exists(AUDIO_OUTPUT_FILE):
            try:
                os.remove(AUDIO_OUTPUT_FILE)
            except PermissionError:
                pass


def speak(text):
    asyncio.run(speak_async(text))


def main():
    print("\n🎓 SGU Admission Counselor Started")
    print("Press Ctrl+C to stop.\n")
    while True:
        try:
            user_text = listen_and_transcribe()
            if not user_text:
                continue
            print(f"Parent: {user_text}")
            if any(w in user_text.lower() for w in ["stop", "exit", "bye", "goodbye"]):
                speak("Thank you for calling. Have a great day!")
                break
            print("🧠 Thinking...")
            reply = get_ai_response(user_text)
            conversation_history.append({"parent": user_text, "counselor": reply})
            speak(reply)
        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print_microphone_diagnostics()
    for f in [AUDIO_INPUT_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass
    main()