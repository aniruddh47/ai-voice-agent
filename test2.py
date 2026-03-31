import os
import json
import time
import asyncio
import threading
import speech_recognition as sr
from faster_whisper import WhisperModel
from edge_tts import Communicate
from playsound import playsound
from dotenv import load_dotenv
from google import genai
import numpy as np
from sentence_transformers import SentenceTransformer

question_cache = {}
cache_questions = []
question_embeddings = []
conversation_history = []

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

load_dotenv()

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small.en")
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
stt_model = None
embedding_model = None
stt_model_lock = threading.Lock()
embedding_model_lock = threading.Lock()
PRELOAD_MODELS_IN_BACKGROUND = os.getenv("PRELOAD_MODELS_IN_BACKGROUND", "0") == "1"


def get_stt_model():
    global stt_model
    if stt_model is None:
        with stt_model_lock:
            if stt_model is None:
                print("⏳ Loading Whisper model (first time)...")
                stt_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return stt_model


def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        with embedding_model_lock:
            if embedding_model is None:
                print("⏳ Loading embedding model (first time)...")
                embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return embedding_model


def preload_models_in_background():
    if not PRELOAD_MODELS_IN_BACKGROUND:
        return

    def _preload_worker():
        try:
            get_stt_model()
            get_embedding_model()
            print("✅ Background model preload complete")
        except Exception as e:
            print(f"⚠️  Background preload failed: {e}")

    threading.Thread(target=_preload_worker, daemon=True).start()
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


def summarize_value(value, max_chars=170):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=True)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text[:max_chars].rstrip() + ("..." if len(text) > max_chars else "")


def extract_relevant_context(user_text):
    text = user_text.lower()
    relevant_parts = []

    topic_rules = [
        (
            ["admission", "apply", "eligibility", "process", "jee", "cet", "document", "fees", "fee"],
            "Admissions",
            COLLEGE_DATA.get("admissions", {}) or COLLEGE_DATA.get("admission_procedures_detailed", {}),
        ),
        (
            ["course", "program", "branch", "department", "btech", "mba", "mca", "engineering"],
            "Programs",
            COLLEGE_DATA.get("departments", {}),
        ),
        (
            ["placement", "salary", "package", "company", "career", "job"],
            "Placements",
            COLLEGE_DATA.get("career_and_placements", {}),
        ),
        (
            ["hostel", "accommodation", "mess", "room", "stay", "food"],
            "Hostel",
            COLLEGE_DATA.get("hostel_detailed", {}) or COLLEGE_DATA.get("campus_life", {}).get("hostel", {}),
        ),
        (
            ["transport", "bus", "route", "pickup", "drop", "travel"],
            "Transport",
            COLLEGE_DATA.get("transport_detailed", {}),
        ),
        (
            ["library", "book", "journal", "digital"],
            "Library",
            COLLEGE_DATA.get("library_detailed", {}),
        ),
        (
            ["sports", "gym", "ground", "court", "athletics"],
            "Sports",
            COLLEGE_DATA.get("sports_facilities_detailed", {}),
        ),
        (
            ["medical", "doctor", "health", "clinic", "ambulance"],
            "Medical",
            COLLEGE_DATA.get("medical_facilities", {}),
        ),
    ]

    for keywords, label, source_data in topic_rules:
        if any(word in text for word in keywords):
            summary = summarize_value(source_data)
            if summary:
                relevant_parts.append(f"{label}: {summary}")

    if not relevant_parts:
        overview = summarize_value(COLLEGE_DATA.get("university_overview", {}), max_chars=240)
        admissions = summarize_value(COLLEGE_DATA.get("admissions", {}), max_chars=220)
        fallback_context = f"Overview: {overview} | Admissions: {admissions}".strip(" |")
        return fallback_context[:650]

    context = " | ".join(relevant_parts)
    return context[:650]


def build_prompt(user_text):
    short_context = extract_relevant_context(user_text)
    prompt = (
        "You are a polite and professional admission counselor for Sanjay Ghodawat University, Kolhapur.\n\n"
        "Answer like a real person on a phone call.\n"
        "Keep answers short (2-3 sentences), natural, and confident.\n"
        "Do not use bullet points or special characters.\n\n"
        "Context:\n"
        f"{short_context}\n\n"
        "Question:\n"
        f"{user_text}\n\n"
        "Answer naturally."
    )
    return prompt


def compute_embedding(text):
    clean_text = (text or "").strip()
    if not clean_text:
        clean_text = "general admission query"
    return get_embedding_model().encode(clean_text, normalize_embeddings=True)


def get_similar_cached_response(query_embedding):
    if not question_embeddings:
        return None
    scores = np.dot(np.vstack(question_embeddings), query_embedding)
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    if best_score > 0.85:
        matched_query = cache_questions[best_idx]
        print(f"⚡ [SEMANTIC CACHE HIT: {best_score:.2f}]")
        return question_cache.get(matched_query)
    return None


def store_in_cache(query, response, embedding):
    if not response:
        return
    normalized_query = query.lower().strip()
    if normalized_query in question_cache:
        question_cache[normalized_query] = response
        return
    question_cache[normalized_query] = response
    cache_questions.append(normalized_query)
    question_embeddings.append(embedding)


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
    segments, _ = get_stt_model().transcribe(
        AUDIO_INPUT_FILE,
        beam_size=1,
        language=WHISPER_LANGUAGE,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    text = " ".join([seg.text for seg in segments]).strip()
    if not text:
        print("⚠️  Speech was captured but transcription is empty. Try reducing background noise or changing mic device.")
    return text


def get_ai_response(text):
    user_query = (text or "").lower().strip()
    if not user_query:
        return "Could you please repeat your question?"

    query_embedding = compute_embedding(user_query)
    cached_response = get_similar_cached_response(query_embedding)
    if cached_response:
        return cached_response

    print("🤔 Thinking...")

    try:
        prompt = build_prompt(text)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        reply = (response.text or "").strip()

        if reply:
            print("Counselor: ", end="", flush=True)
            for word in reply.split():
                print(word, end=" ", flush=True)
                time.sleep(0.03)
            print()
            store_in_cache(user_query, reply, query_embedding)
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
    preload_models_in_background()
    while True:
        try:
            user_text = listen_and_transcribe()
            if not user_text:
                continue
            print(f"Parent: {user_text}")
            if any(w in user_text.lower() for w in ["stop", "exit", "bye", "goodbye"]):
                speak("Thank you for calling. Have a great day!")
                break
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