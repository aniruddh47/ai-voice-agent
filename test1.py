import streamlit as st
import json
import os
import base64
import time
from pathlib import Path
from dotenv import load_dotenv
from audio_recorder_streamlit import audio_recorder

load_dotenv()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="SGU Admission Counselor",
    page_icon="\U0001F393",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        min-height: 100vh;
    }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 1rem 2rem; max-width: 800px; margin: auto; }

    .app-title {
        text-align: center;
        padding: 1.5rem 0 0.5rem;
    }
    .app-title h1 {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .app-title p {
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }

    .chat-container {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.2rem;
        height: 420px;
        overflow-y: auto;
        margin-bottom: 0.8rem;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .chat-container::-webkit-scrollbar { width: 4px; }
    .chat-container::-webkit-scrollbar-track { background: transparent; }
    .chat-container::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }

    .msg-user {
        align-self: flex-end;
        background: linear-gradient(135deg, #7c3aed, #2563eb);
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 75%;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .msg-ai {
        align-self: flex-start;
        background: rgba(255,255,255,0.07);
        color: #e2e8f0;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        max-width: 80%;
        font-size: 0.9rem;
        line-height: 1.5;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .msg-label {
        font-size: 0.7rem;
        color: #64748b;
        margin-bottom: 4px;
    }
    .msg-time {
        font-size: 0.68rem;
        color: #475569;
        margin-top: 4px;
        text-align: right;
    }
    .empty-chat {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #475569;
        gap: 8px;
    }
    .empty-chat span { font-size: 2.5rem; }
    .empty-chat p { font-size: 0.9rem; margin: 0; }

    .stTextInput input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        padding: 12px 16px !important;
        font-size: 0.9rem !important;
    }
    .stTextInput input::placeholder { color: #64748b !important; }
    .stTextInput input:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 2px rgba(124,58,237,0.2) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #2563eb);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(124,58,237,0.4);
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- HELPERS ---
def get_system_instruction():
    try:
        with open("college_info.json", "r", encoding="utf-8") as f:
            info = json.load(f)
        fees = {}
        for k, v in info.get("courses", {}).get("undergraduate", {}).items():
            fees[k] = v.get("fees")
        for k, v in info.get("courses", {}).get("postgraduate", {}).items():
            fees[k] = v.get("fees")
        adm = info.get("admissions", {})
        return f"""You are a friendly admission counselor for {info.get('college_name','Sanjay Ghodawat University')}.
Rules: Keep answers under 3 sentences. Be warm and helpful.
Knowledge: Admissions open {adm.get('start_date')} - {adm.get('last_date')}.
Eligibility: {adm.get('eligibility')}. Fees: {fees}.
Placements: {info.get('placements')}. Hostel: {info.get('hostel')}."""
    except FileNotFoundError:
        return "You are a helpful admission counselor for Sanjay Ghodawat University. Keep answers brief and warm."


def get_gemini_chat_response(user_msg, history):
    try:
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "GEMINI_API_KEY not found. Please add it to your .env file."
        client = genai.Client(api_key=api_key)
        contents = []
        for m in history[-5:]:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_msg)]))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=get_system_instruction()),
            contents=contents
        )
        return response.text
    except ImportError:
        return "google-genai package not installed. Run: pip install google-genai"
    except Exception as e:
        return f"API Error: {str(e)}"


def transcribe_audio_and_respond(audio_bytes):
    try:
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Could not hear you", "API key missing"
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=get_system_instruction()),
            contents=[
                types.Content(parts=[
                    types.Part(inline_data=types.Blob(mime_type="audio/webm", data=audio_bytes)),
                    types.Part.from_text(
                        text="First transcribe what the user said in [TRANSCRIPT: ...], then answer as the counselor."
                    )
                ])
            ]
        )
        raw = response.text
        transcript = ""
        reply = raw
        if "[TRANSCRIPT:" in raw:
            start = raw.index("[TRANSCRIPT:") + len("[TRANSCRIPT:")
            end = raw.index("]", start)
            transcript = raw[start:end].strip()
            reply = raw[end + 1:].strip()
        return transcript, reply
    except Exception as e:
        return "Could not process audio", f"Error: {str(e)}"


# --- HEADER ---
st.markdown("""
<div class="app-title">
    <h1>SGU Admission Counselor</h1>
    <p>Ask anything about admissions, fees, hostel, or placements</p>
</div>
""", unsafe_allow_html=True)

# --- CHAT MESSAGES ---
chat_html = '<div class="chat-container" id="chatbox">'
if not st.session_state.messages:
    chat_html += """<div class="empty-chat">
        <span>&#129302;</span>
        <p>Hi! I'm your SGU Admission Counselor.</p>
        <p style="color:#334155">Type a message or tap the mic to talk!</p>
    </div>"""
else:
    for msg in st.session_state.messages:
        t = msg.get("time", "")
        if msg["role"] == "user":
            chat_html += f"""<div>
                <div class="msg-label" style="text-align:right">You</div>
                <div class="msg-user">{msg["content"]}<div class="msg-time">{t}</div></div>
            </div>"""
        else:
            chat_html += f"""<div>
                <div class="msg-label">Counselor</div>
                <div class="msg-ai">{msg["content"]}<div class="msg-time">{t}</div></div>
            </div>"""
chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

st.markdown("""<script>
    const chatbox = document.getElementById('chatbox');
    if (chatbox) chatbox.scrollTop = chatbox.scrollHeight;
</script>""", unsafe_allow_html=True)

# --- INPUT ROW: text + send ---
inp_col, send_col = st.columns([5, 1])

with inp_col:
    user_input = st.text_input(
        "", placeholder="Type your question here...",
        key="chat_input", label_visibility="collapsed"
    )
with send_col:
    send_clicked = st.button("Send", use_container_width=True)

# Handle text send
if send_clicked and user_input.strip():
    st.session_state.messages.append(
        {"role": "user", "content": user_input.strip(), "time": time.strftime("%H:%M")}
    )
    with st.spinner("Counselor is typing..."):
        reply = get_gemini_chat_response(user_input.strip(), st.session_state.messages[:-1])
    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "time": time.strftime("%H:%M")}
    )
    st.rerun()

# --- MIC RECORDING ---
st.markdown(
    "<p style='color:#64748b;text-align:center;font-size:0.8rem;margin-top:0.5rem;'>"
    "Click the mic below to record your voice question</p>",
    unsafe_allow_html=True,
)

audio_bytes = audio_recorder(
    text="",
    recording_color="#e74c3c",
    neutral_color="#7c3aed",
    icon_size="2x",
    pause_threshold=10.0,
    sample_rate=16000,
    key="mic_recorder"
)

if audio_bytes:
    # Prevent re-processing the same recording
    audio_hash = hash(audio_bytes)
    if st.session_state.get("last_audio_hash") != audio_hash:
        st.session_state.last_audio_hash = audio_hash
        st.audio(audio_bytes, format="audio/wav")
        with st.spinner("Counselor is listening & thinking..."):
            transcript, response = transcribe_audio_and_respond(audio_bytes)
        if transcript:
            st.session_state.messages.append(
                {"role": "user", "content": f"\U0001f3a4 {transcript}", "time": time.strftime("%H:%M")}
            )
        st.session_state.messages.append(
            {"role": "assistant", "content": response, "time": time.strftime("%H:%M")}
        )
        st.rerun()

# --- CLEAR CHAT ---
if st.session_state.messages:
    st.markdown("")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
