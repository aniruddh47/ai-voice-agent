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

def build_prompt(user_text):
    try:
        with open(resolve_data_file("college_info.json"), "r", encoding="utf-8") as f:
            COLLEGE_INFO = json.load(f)
    except FileNotFoundError:
        return "You are an admission counselor. Keep answers short."

    text = user_text.lower()
    
    prompt = f"""
    You are a polite and professional admission counselor for {COLLEGE_INFO.get('college_name')}.
    You are speaking on a phone call with a parent.
    
    CRITICAL RULES:
    - Keep your answer short (maximum 2 sentences).
    - Speak naturally and conversationally.
    - NEVER use special formatting like * or #.
    """

    prompt += "\nRelevant Data for this specific question:\n"
    data_added = False

    # Check for Admissions & Eligibility
    if any(word in text for word in ["admission", "date", "apply", "eligibility", "process", "exam", "document"]):
        prompt += f"- Admissions Data: {COLLEGE_INFO.get('admissions')}\n"
        data_added = True
        
    # Check for B.Tech / Engineering
    if any(word in text for word in ["btech", "b.tech", "engineering", "cse", "aiml", "mechanical", "civil"]):
        prompt += f"- B.Tech Data: {COLLEGE_INFO.get('courses', {}).get('undergraduate', {}).get('B.Tech')}\n"
        data_added = True

    # Check for PG / MBA / M.Tech
    if any(word in text for word in ["mba", "m.tech", "pg", "master"]):
        prompt += f"- PG Courses: {COLLEGE_INFO.get('courses', {}).get('postgraduate')}\n"
        data_added = True

    # Check for Placements
    if any(word in text for word in ["placement", "salary", "package", "company", "recruit"]):
        prompt += f"- Placements: {COLLEGE_INFO.get('placements')}\n"
        data_added = True

    # Check for Hostel, Mess & Facilities
    if any(word in text for word in ["hostel", "mess", "food", "stay", "facility", "sport", "library", "bus", "transport"]):
        prompt += f"- Hostel: {COLLEGE_INFO.get('hostel')}\n"
        prompt += f"- Facilities: {COLLEGE_INFO.get('facilities')}\n"
        data_added = True

    # FALLBACK (If they ask a general question)
    if not data_added:
        prompt += f"- Location: {COLLEGE_INFO.get('location')} | Accreditations: {COLLEGE_INFO.get('accreditations')}\n"

    # Append the actual user question
    prompt += f"\nParent's Question: {user_text}"
    
    return prompt

def listen_and_transcribe():
    with sr.Microphone() as source:
        print("\n🎤 Listening... (Speak now)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)
        
        with open(AUDIO_INPUT_FILE, "wb") as f:
            f.write(audio.get_wav_data())
            
    print("⏳ Transcribing...")
    segments, _ = stt_model.transcribe(AUDIO_INPUT_FILE, beam_size=5)
    text = " ".join([segment.text for segment in segments]).strip()
    return text

def get_ai_response(text):
    global question_cache
    user_query = text.lower().strip()

    similar_questions = difflib.get_close_matches(user_query, question_cache.keys(), n=1, cutoff=0.80)
    
    if similar_questions:
        print("⚡ [CACHE HIT] I remember this! Answering instantly without API...")

        return question_cache[similar_questions[0]]

   
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
        else:
            return "I didn't quite catch that. Could you repeat?"
            
    except Exception as e:
        print(f"AI Error: {e}")
        return "I'm having trouble connecting to my database. Give me a second."

async def speak_async(text):
    """Converts text to speech using Edge TTS (Microsoft online voices)."""
    print(f"Counselor: {text}")
    clean_text = text.replace("*", "").replace("#", "")
    
    try:
        print("⏳ Generating speech...")
        communicate = Communicate(clean_text, TTS_VOICE)
        await communicate.save(AUDIO_OUTPUT_FILE)
        
        file_size = os.path.getsize(AUDIO_OUTPUT_FILE)
        print(f"✅ Audio file created ({file_size} bytes)")
        
        print("🔊 Playing response...")
        playsound(AUDIO_OUTPUT_FILE)
        print("🎵 Playback finished!")
        
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
    """Wrapper to run async speak function."""
    asyncio.run(speak_async(text))

def main():
    print("\n🎓 Admission Counselor Started")
    print("Press Ctrl+C to stop.")
    
    while True:
        try:
            user_text = listen_and_transcribe()
            if not user_text:
                continue
                
            print(f"Parent: {user_text}")
            
            if "stop" in user_text.lower() or "exit" in user_text.lower():
                print("Ending session...")
                break

            print("🧠 Thinking...")
            reply = get_ai_response(user_text)
            
            
            conversation_history.append({
                "parent": user_text,
                "counselor": reply
            })
            
            speak(reply)

        except KeyboardInterrupt:
            print("\nSession ended manually.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    if os.path.exists(AUDIO_INPUT_FILE):
        try: os.remove(AUDIO_INPUT_FILE)
        except: pass
    main()