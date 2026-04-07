import os
import asyncio
import time
import threading
import speech_recognition as sr
from faster_whisper import WhisperModel
from edge_tts import Communicate
from playsound import playsound
from dotenv import load_dotenv
from google import genai

from backend.utils import (
    SemanticCache,
    EmbeddingService,
    SemanticRetriever,
    load_and_chunk_knowledge
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
CACHE_PATH = os.path.join(BASE_DIR, "backend", "cache", "cache.json")

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
WHISPER_MODEL = os.getenv("WHISPER_MODEL_SIZE", "small.en")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")
TTS_VOICE = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")
MIC_DEVICE_INDEX = os.getenv("MIC_DEVICE_INDEX")
MIC_DEVICE_INDEX = int(MIC_DEVICE_INDEX) if MIC_DEVICE_INDEX and MIC_DEVICE_INDEX.isdigit() else None

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", "0.15"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "1600"))
CACHE_THRESHOLD = float(os.getenv("CACHE_THRESHOLD", "0.90"))
DEBUG = os.getenv("RAG_DEBUG", "1") == "1"
LISTEN_TIMEOUT = float(os.getenv("LISTEN_TIMEOUT_SEC", "8"))
PHRASE_TIME_LIMIT = float(os.getenv("PHRASE_TIME_LIMIT_SEC", "12"))
AMBIENT_SEC = float(os.getenv("AMBIENT_CALIBRATION_SEC", "1.0"))

client = genai.Client(api_key=API_KEY)

# Global models
stt_model = None
stt_model_lock = threading.Lock()
embeddings_service = None
retriever = None
cache = None


def get_stt_model():
    global stt_model
    if stt_model is None:
        with stt_model_lock:
            if stt_model is None:
                print("⏳ Loading Whisper model...")
                stt_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return stt_model


def init_rag():
    global embeddings_service, retriever, cache
    if embeddings_service is None:
        try:
            print("⏳ Initializing RAG system...")
            embeddings_service = EmbeddingService(model_name="all-MiniLM-L6-v2")
            embeddings_service.preload()
            
            chunks = load_and_chunk_knowledge(DATA_DIR)
            chunk_embeddings = embeddings_service.encode_many(chunks)
            
            retriever = SemanticRetriever(similarity_threshold=RAG_THRESHOLD, debug=DEBUG)
            retriever.build(chunks, chunk_embeddings)
            
            cache = SemanticCache(cache_path=CACHE_PATH, threshold=CACHE_THRESHOLD, debug=DEBUG)
            print("✅ RAG system ready")
        except Exception as e:
            print(f"⚠️ RAG initialization failed: {e}")
            print("⚠️ Continuing with basic operation (cache only)")
            embeddings_service = EmbeddingService(model_name="all-MiniLM-L6-v2")
            cache = SemanticCache(cache_path=CACHE_PATH, threshold=CACHE_THRESHOLD, debug=DEBUG)


def list_microphones():
    try:
        names = sr.Microphone.list_microphone_names()
        print("🎙️  Available microphones:")
        for idx, name in enumerate(names):
            marker = " <- selected" if MIC_DEVICE_INDEX == idx else ""
            print(f"  [{idx}] {name}{marker}")
    except Exception as e:
        print(f"⚠️ Could not list microphones: {e}")


recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.5


def listen_and_transcribe():
    wav_path = os.path.join(BASE_DIR, "backend", "cache", "temp_input.wav")
    try:
        with sr.Microphone(device_index=MIC_DEVICE_INDEX) as source:
            print("\n🎤 Listening... (Speak now)")
            recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_SEC)
            audio = recognizer.listen(
                source,
                timeout=LISTEN_TIMEOUT,
                phrase_time_limit=PHRASE_TIME_LIMIT,
            )
            with open(wav_path, "wb") as f:
                f.write(audio.get_wav_data())
    except sr.WaitTimeoutError:
        return ""
    except Exception as e:
        print(f"❌ Microphone error: {e}")
        return ""

    if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
        return ""

    print("⏳ Transcribing...")
    segments, _ = get_stt_model().transcribe(
        wav_path,
        beam_size=1,
        language=WHISPER_LANGUAGE,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    text = " ".join([seg.text for seg in segments]).strip()
    return text


def get_rag_context(question):
    """Get RAG context for the question"""
    if retriever is None:
        print("⚠️ RAG not available, using fallback")
        return "General admission information available. Please ask about our programs, facilities, or admission process."
    
    try:
        q_emb = embeddings_service.encode(question)
        retrieved = retriever.search(q_emb, top_k=RAG_TOP_K)
        
        fallback_context = "General admission information available."
        context_text = retriever.build_context(
            items=retrieved,
            fallback_context=fallback_context,
            max_chars=MAX_CONTEXT_CHARS,
        )
        return context_text
    except Exception as e:
        print(f"⚠️ RAG retrieval failed: {e}")
        return "General admission information available."


def get_cached_response(question):
    """Check cache for similar question"""
    if cache is None:
        return None
    
    q_emb = embeddings_service.encode(question)
    cached, score = cache.lookup(q_emb)
    
    if cached and score >= CACHE_THRESHOLD:
        return cached
    return None


def cache_response(question, response):
    """Cache the response"""
    if cache is None:
        return
    
    q_emb = embeddings_service.encode(question)
    cache.add(question, response, q_emb)


def build_prompt(question, context):
    """Build prompt for LLM with professional system guidance"""
    return (
        "You are an AI Admission Counsellor for Sanjay Ghodawat University (SGU).\n"
        "Your job is to provide accurate, detailed, and helpful information about SGU only.\n\n"
        "CRITICAL RULES:\n"
        "- Answer questions clearly, completely, and with full details.\n"
        "- Do NOT use fillers like 'Oh', 'Yeah', 'Thanks', 'Okay', 'Absolutely'.\n"
        "- Speak naturally like a professional admission counsellor.\n"
        "- Do NOT mention any other university except SGU/Sanjay Ghodawat University.\n"
        "- Do NOT hallucinate information - only use provided context.\n"
        "- If you don't know something, say: 'I can help you connect with the admissions team for more details.'\n"
        "- Provide 3-5 sentences of detailed information per response.\n\n"
        "Context About SGU:\n"
        f"{context}\n\n"
        "User Question:\n"
        f"{question}\n\n"
        "Response (professional and detailed):"
    )


def get_ai_response(text):
    """Get AI response using RAG"""
    user_query = (text or "").lower().strip()
    if not user_query:
        return "Could you please repeat your question?"

    # Check cache first
    cached = get_cached_response(user_query)
    if cached:
        print("⚡ Returning cached answer")
        return cached

    # Get RAG context
    print("🔎 Retrieving context...")
    context = get_rag_context(text)
    
    # Build prompt
    prompt = build_prompt(text, context)
    print("🤔 Thinking...")

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={"temperature": 0.5, "max_output_tokens": 1000},
        )
        reply = (response.text or "").strip()

        if reply:
            # Cache this response
            cache_response(user_query, reply)
            return reply
        return "I didn't quite catch that. Could you repeat?"
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return "I'm having trouble connecting right now. Please try again."


async def speak_async(text):
    """Speak the text using Edge TTS"""
    audio_file = os.path.join(BASE_DIR, "backend", "cache", "response.mp3")
    clean_text = text.replace("*", "").replace("#", "")
    try:
        communicate = Communicate(clean_text, TTS_VOICE)
        await communicate.save(audio_file)
        playsound(audio_file)
    except Exception as e:
        print(f"⚠️ [TTS Error]: {e}")
    finally:
        time.sleep(0.5)
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except:
                pass


def speak(text):
    """Speak helper"""
    print(f"Counselor: {text}")
    asyncio.run(speak_async(text))


def main():
    print("\n🎓 SGU Admission Counselor Started")
    print("Press Ctrl+C to stop.\n")
    
    list_microphones()
    init_rag()
    print("✅ READY - Listening loop active\n")
    
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
            speak(reply)
        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
