import os
import json
import time
import asyncio
import re
import speech_recognition as sr
from faster_whisper import WhisperModel
from edge_tts import Communicate
from playsound import playsound
from dotenv import load_dotenv
from google import genai
import difflib

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    VECTOR_SEARCH_AVAILABLE = True
except Exception:
    VECTOR_SEARCH_AVAILABLE = False
    np = None
    SentenceTransformer = None

question_cache = {}
conversation_history = []

WHISPER_MODEL_SIZE = "small.en"
AUDIO_INPUT_FILE = "temp_input.wav"
AUDIO_OUTPUT_FILE = "response.mp3"
TTS_VOICE = "en-IN-NeerjaNeural"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def resolve_data_file(filename):
    data_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(data_path):
        return data_path
    return os.path.join(BASE_DIR, filename)

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise Exception("GEMINI_API_KEY missing from environment variables.")

client = genai.Client(api_key=API_KEY)

print("⏳ Loading Faster-Whisper Model...")
stt_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
recognizer = sr.Recognizer()

# Intent map is used by normalization and simple fallback relevance scoring.
INTENT_MAP = {
    "hostel": ["hostel", "accommodation", "room", "stay", "mess", "food", "resident"],
    "fees": ["fee", "fees", "cost", "price", "how much", "charges", "pay"],
    "courses": ["course", "program", "branch", "department", "btech", "study", "mba", "mca"],
    "placement": ["placement", "job", "salary", "package", "company", "recruit", "career"],
    "admission": ["admission", "apply", "eligibility", "join", "entrance", "jee", "cet"],
    "transport": ["transport", "bus", "route", "pickup", "drop", "commute", "travel"],
    "sports": ["sports", "gym", "cricket", "football", "court", "ground", "athletics"],
    "library": ["library", "book", "journal", "reading", "study hall", "digital"],
    "medical": ["medical", "clinic", "doctor", "health", "hospital", "ambulance"],
}

PREGENED_ANSWERS = {
    "fees": "For exact fees, we can share the latest official structure during counseling. Typically, tuition depends on the chosen program and hostel or transport is charged separately.",
    "hostel": "We provide separate hostel facilities with student support and essential amenities for comfortable campus living. Availability, room options, and meal details are explained during admission counseling.",
    "placement": "The university has dedicated placement support with training and recruiter engagement for eligible students. Placement outcomes vary by branch, skills, and market conditions each year.",
    "admission": "Admissions are based on eligibility criteria, accepted entrance pathways, and document verification. You can apply through the official process and our team can guide you step by step.",
    "courses": "We offer multiple undergraduate and postgraduate programs across engineering, management, and other disciplines. Program-specific eligibility and intake details are available through the admissions desk.",
}


# ── NEW: Load all JSON files at startup ──────────────────────────────────────
def load_all_college_data():
    """Merges all JSON data files into one dictionary at startup."""
    data = {}

    def deep_merge_dict(target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge_dict(target[key], value)
            else:
                target[key] = value

    json_files = [
        "college_info.json",
        "facilities_detailed.json",
        "departments_info.json",
        "admission_procedures.json",
    ]
    for fname in json_files:
        file_path = resolve_data_file(fname)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        deep_merge_dict(data, loaded)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Could not parse {file_path}: {e}")
        else:
            print(f"⚠️  File not found: {file_path}")
    return data

COLLEGE_DATA = load_all_college_data()  # Loaded ONCE at startup


def get_slim_data(data_dict, keep_keys):
    """Keeps only essential keys for compact prompt context."""
    if not isinstance(data_dict, dict):
        return data_dict
    slim = {k: data_dict[k] for k in keep_keys if k in data_dict}
    return slim if slim else data_dict


def normalize_query(text):
    text = re.sub(r"\s+", " ", text.lower().strip())
    for intent, keywords in INTENT_MAP.items():
        if any(kw in text for kw in keywords):
            return intent
    return text


def json_to_text(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ": ")) if isinstance(value, (dict, list)) else str(value)


def build_knowledge_chunks():
    admissions = get_slim_data(COLLEGE_DATA.get("admissions", {}), [
        "eligibility", "application_process", "important_dates", "accepted_exams", "documents_required", "fees"
    ])
    departments = get_slim_data(COLLEGE_DATA.get("departments", {}), [
        "btech_software", "btech_core", "programs", "undergraduate", "postgraduate"
    ])
    placements = get_slim_data(COLLEGE_DATA.get("career_and_placements", {}), [
        "average_package", "highest_package", "top_recruiters", "training", "placement_stats"
    ])
    hostel = get_slim_data(COLLEGE_DATA.get("hostel_detailed", {}), [
        "total_capacity", "room_types", "mess_details", "security", "fees_structure"
    ])
    transport = get_slim_data(COLLEGE_DATA.get("transport_detailed", {}), [
        "routes", "coverage", "timings", "fees", "fleet"
    ])
    sports = get_slim_data(COLLEGE_DATA.get("sports_facilities_detailed", {}), [
        "indoor", "outdoor", "grounds", "coaching", "events"
    ])
    library = get_slim_data(COLLEGE_DATA.get("library_detailed", {}), [
        "books", "journals", "digital_resources", "timings", "facilities"
    ])
    medical = get_slim_data(COLLEGE_DATA.get("medical_facilities", {}), [
        "clinic", "doctor_availability", "ambulance", "emergency_support"
    ])

    return [
        {"topic": "admission", "keywords": INTENT_MAP["admission"], "text": json_to_text(admissions)},
        {"topic": "courses", "keywords": INTENT_MAP["courses"], "text": json_to_text(departments)},
        {"topic": "placement", "keywords": INTENT_MAP["placement"], "text": json_to_text(placements)},
        {"topic": "hostel", "keywords": INTENT_MAP["hostel"], "text": json_to_text(hostel)},
        {"topic": "transport", "keywords": INTENT_MAP["transport"], "text": json_to_text(transport)},
        {"topic": "sports", "keywords": INTENT_MAP["sports"], "text": json_to_text(sports)},
        {"topic": "library", "keywords": INTENT_MAP["library"], "text": json_to_text(library)},
        {"topic": "medical", "keywords": INTENT_MAP["medical"], "text": json_to_text(medical)},
    ]


KNOWLEDGE_CHUNKS = build_knowledge_chunks()
EMBEDDER = None
CHUNK_EMBEDDINGS = None

if VECTOR_SEARCH_AVAILABLE:
    try:
        print("⏳ Loading sentence-transformer for vector search...")
        EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
        CHUNK_EMBEDDINGS = EMBEDDER.encode(
            [c["text"] for c in KNOWLEDGE_CHUNKS],
            normalize_embeddings=True,
        )
        print("✅ Vector index ready")
    except Exception as e:
        print(f"⚠️  Vector search unavailable, using keyword fallback: {e}")
        EMBEDDER = None
        CHUNK_EMBEDDINGS = None


def get_relevant_chunks(user_query, top_k=2):
    if EMBEDDER is not None and CHUNK_EMBEDDINGS is not None:
        query_embedding = EMBEDDER.encode([user_query], normalize_embeddings=True)[0]
        scores = np.dot(CHUNK_EMBEDDINGS, query_embedding)
        top_indices = scores.argsort()[-top_k:][::-1]
        return [KNOWLEDGE_CHUNKS[i] for i in top_indices]

    query_lower = user_query.lower()
    scored = []
    for chunk in KNOWLEDGE_CHUNKS:
        score = sum(1 for kw in chunk.get("keywords", []) if kw in query_lower)
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item[1] for item in scored[:top_k]]
    if not any(score > 0 for score, _ in scored[:top_k]):
        return KNOWLEDGE_CHUNKS[:top_k]
    return selected


# ── FIXED: build_prompt now reads from the merged COLLEGE_DATA ───────────────
def build_prompt(user_text):
    overview = COLLEGE_DATA.get("university_overview", {})
    relevant_chunks = get_relevant_chunks(user_text, top_k=2)

    prompt = f"""You are a polite and professional admission counselor for Sanjay Ghodawat University (SGU), Kolhapur.
You are speaking on a phone call with a parent or prospective student.

CRITICAL RULES:
- Keep your answer short (maximum 2-3 sentences).
- Speak naturally and conversationally, like a real phone call.
- NEVER use special formatting like *, #, or bullet points.
- If exact data is unavailable, give a helpful general answer and suggest the admissions desk for confirmation.
- Always sound warm, confident, and helpful.

"""

    prompt += "=== RELEVANT COLLEGE DATA ===\n"
    prompt += f"COLLEGE OVERVIEW: {json_to_text(overview)}\n"
    for chunk in relevant_chunks:
        prompt += f"{chunk['topic'].upper()}: {chunk['text']}\n"

    prompt += f"\n=== PARENT'S QUESTION ===\n{user_text}\n"
    prompt += "\nAnswer naturally in 2-3 sentences using only the relevant data above whenever possible."

    return prompt


# ── Rest of your code unchanged ──────────────────────────────────────────────
def listen_and_transcribe():
    with sr.Microphone() as source:
        print("\n🎤 Listening... (Speak now)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
        with open(AUDIO_INPUT_FILE, "wb") as f:
            f.write(audio.get_wav_data())
    print("⏳ Transcribing...")
    segments, _ = stt_model.transcribe(
        AUDIO_INPUT_FILE,
        beam_size=5,
        language="en",
        vad_filter=True,
        condition_on_previous_text=False,
    )
    return " ".join([seg.text for seg in segments]).strip()


def get_ai_response(text):
    user_query = text.lower().strip()
    cache_key = normalize_query(user_query)

    if cache_key in PREGENED_ANSWERS:
        print("⚡ [PRE-GEN HIT]")
        return PREGENED_ANSWERS[cache_key]

    similar = difflib.get_close_matches(cache_key, question_cache.keys(), n=1, cutoff=0.75)
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
            question_cache[cache_key] = reply
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
    for f in [AUDIO_INPUT_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass
    main()