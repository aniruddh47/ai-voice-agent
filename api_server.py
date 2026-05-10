import os
import json
import time
import re
import difflib
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai

from backend.utils import (
    SemanticCache,
    EmbeddingService,
    SemanticRetriever,
    load_and_chunk_knowledge,
    ChatHistoryManager
)

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

API_KEY = (os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'"))
LLM_ENABLED = bool(API_KEY)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL_NAME = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-flash").strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
CACHE_PATH = os.path.join(BASE_DIR, "backend", "cache", "cache.json")
AERONAUTICAL_DETAILS_PATH = os.path.join(DATA_DIR, "aeronautical_admission_details.json")
DEPARTMENTS_INFO_PATH = os.path.join(DATA_DIR, "departments_info.json")
COLLEGE_INFO_PATH = os.path.join(DATA_DIR, "college_info.json")

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", "0.15"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "1600"))
CACHE_THRESHOLD = float(os.getenv("CACHE_THRESHOLD", "0.90"))
DEBUG = os.getenv("RAG_DEBUG", "1") == "1"

client = None
if LLM_ENABLED:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"⚠️ Gemini client initialization failed, running in fallback mode: {e}")
        LLM_ENABLED = False
else:
    print("⚠️ GEMINI_API_KEY not set. Running in fallback mode (RAG/rules only).")

# Global services
embeddings_service = None
retriever = None
cache = None
chat_history_manager = None


def init_services():
    """Initialize RAG and embedding services"""
    global embeddings_service, retriever, cache, chat_history_manager
    
    if embeddings_service is not None:
        return  # Already initialized
    
    try:
        print("⏳ Initializing RAG services...")
        embeddings_service = EmbeddingService(model_name="all-MiniLM-L6-v2")
        embeddings_service.preload()
        
        chunks = load_and_chunk_knowledge(DATA_DIR)
        chunk_embeddings = embeddings_service.encode_many(chunks)
        
        retriever = SemanticRetriever(similarity_threshold=RAG_THRESHOLD, debug=DEBUG)
        retriever.build(chunks, chunk_embeddings)
        
        cache = SemanticCache(cache_path=CACHE_PATH, threshold=CACHE_THRESHOLD, debug=DEBUG)
        
        # Initialize chat history manager
        chat_history_manager = ChatHistoryManager()
        
        print("✅ RAG services ready")
    except Exception as e:
        print(f"⚠️ Service initialization failed: {e}")


def get_rag_context(question):
    """Get RAG context for the question"""
    if retriever is None:
        fallback_context = "General admission information available."
        targeted = _get_targeted_context(question)
        return (f"{fallback_context}\n\n{targeted}" if targeted else fallback_context)
    
    try:
        q_emb = embeddings_service.encode(question)
        retrieved = retriever.search(q_emb, top_k=RAG_TOP_K)
        
        fallback_context = "General admission information available."
        context_text = retriever.build_context(
            items=retrieved,
            fallback_context=fallback_context,
            max_chars=MAX_CONTEXT_CHARS,
        )

        targeted = _get_targeted_context(question)
        if targeted:
            remaining = max(200, MAX_CONTEXT_CHARS - len(targeted) - 2)
            base = (context_text or "")[:remaining].rstrip()
            context_text = f"{base}\n\n{targeted}" if base else targeted

        return context_text
    except Exception as e:
        print(f"⚠️ RAG retrieval failed: {e}")
        fallback_context = "General admission information available."
        targeted = _get_targeted_context(question)
        return (f"{fallback_context}\n\n{targeted}" if targeted else fallback_context)


def _get_targeted_context(question):
    """Add branch-specific context for frequent queries to improve fallback quality."""
    q = (question or "").lower()

    if not re.search(r"aeronautical|aeronotical|aero", q):
        return ""

    if not os.path.exists(AERONAUTICAL_DETAILS_PATH):
        return ""

    try:
        with open(AERONAUTICAL_DETAILS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        fees = data.get("aeronautical_fees", {})
        steps = data.get("aeronautical_admission_procedure", {})
        exams = data.get("aeronautical_eligibility_and_exam", {})

        lines = [
            "Aeronautical Engineering (SGU) quick details:",
            f"- Annual fee: {fees.get('annual_tuition_fee', 'Refer SGU admission office for latest fee circular.')}",
            f"- First installment: {fees.get('first_installment_at_admission', 'As per SGU counseling allotment.')}",
            f"- Eligibility: {exams.get('minimum_qualification', '12th PCM or equivalent as per university norms.')}",
            f"- Accepted exams: {', '.join(exams.get('accepted_exams', ['JEE Main', 'MHT-CET']))}",
            f"- Procedure: {steps.get('step_1', '')} {steps.get('step_2', '')} {steps.get('step_3', '')} {steps.get('step_4', '')}".strip(),
        ]

        return "\n".join(lines)
    except Exception as e:
        print(f"⚠️ Targeted context load failed: {e}")
        return ""


def build_targeted_branch_response(question):
    """Build deterministic response for branch-specific admission questions."""
    q = (question or "").lower()
    if not re.search(r"aeronautical|aeronotical|aero", q):
        return None

    targeted = _get_targeted_context(question)
    if not targeted:
        return None

    return (
        "Here are SGU Aeronautical Engineering admission details I can confirm right now. "
        "\n" + targeted
    )


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_catalog_response(question):
    """Return precise responses for high-level catalog questions (departments/programs)."""
    q = (question or "").lower()
    if not q:
        return None

    asks_department_count = bool(re.search(r"how\s+many\s+depart|number\s+of\s+depart", q))
    asks_department_list = bool(re.search(r"list\s+depart|which\s+depart|what\s+depart", q))
    asks_programs = bool(re.search(r"what\s+program|which\s+program|programs\s+do\s+you\s+offer|courses\s+do\s+you\s+offer", q))

    if not (asks_department_count or asks_department_list or asks_programs):
        return None

    dep_data = _read_json(DEPARTMENTS_INFO_PATH) or {}
    dep_map = dep_data.get("departments", {}) if isinstance(dep_data, dict) else {}
    dep_names = list(dep_map.keys()) if isinstance(dep_map, dict) else []

    college_data = _read_json(COLLEGE_INFO_PATH) or {}
    college_deps = college_data.get("departments", {}) if isinstance(college_data, dict) else {}

    if asks_department_count or asks_department_list:
        if not dep_names:
            return "I am unable to read the department list right now. Please try again."

        names_text = ", ".join(dep_names)
        return (
            f"SGU currently has {len(dep_names)} major departments in my available data. "
            f"They are: {names_text}."
        )

    # Program offerings response from category-wise structure in college_info.json.
    categories = []
    if isinstance(college_deps, dict):
        for category, payload in college_deps.items():
            if not isinstance(payload, dict):
                continue
            details = payload.get("course_details", {})
            if isinstance(details, dict) and details:
                categories.append((category, list(details.keys())))

    if categories:
        lines = []
        for category, programs in categories:
            category_title = category.replace("_", " ").title()
            lines.append(f"{category_title}: {', '.join(programs)}")
        return "SGU programs available in my data are: " + " | ".join(lines)

    return "I can share SGU program details, but I am unable to read the updated course catalog right now."


def get_cached_response(question):
    """Check cache for similar question"""
    if cache is None:
        return None
    
    try:
        q_emb = embeddings_service.encode(question)
        cached, score = cache.lookup(q_emb)
        
        if cached and score >= CACHE_THRESHOLD:
            return cached
        return None
    except Exception as e:
        print(f"⚠️ Cache lookup failed: {e}")
        return None


def cache_response(question, response):
    """Cache the response"""
    if cache is None:
        return
    
    try:
        q_emb = embeddings_service.encode(question)
        cache.add(question, response, q_emb)
    except Exception as e:
        print(f"⚠️ Cache storage failed: {e}")


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


def build_rule_based_response(user_message):
    """Handle greetings/small-talk without calling LLM."""
    msg = (user_message or "").strip().lower()
    if not msg:
        return None

    greeting_patterns = [
        r"^(hi|hello|hey|yo|hii|heyy|namaste|good morning|good afternoon|good evening)[!.\s]*$",
        r"^(hi|hello|hey|yo)\s+(bro|sir|maam|mam|bhai|buddy)[!.\s]*$",
        r"^(thanks|thank you|thx)[!.\s]*$",
    ]

    for pattern in greeting_patterns:
        if re.match(pattern, msg):
            if re.match(r"^(thanks|thank you|thx)", msg):
                return "You are welcome. I am here to help with SGU admissions, fees, eligibility, placements, hostel, scholarships, and documents."
            return "Hello. Welcome to SGU Admission Counselor. How can I help you today?"

    small_talk_patterns = [
        r"\bhow are you\b",
        r"\bhow r u\b",
        r"\bwhat'?s up\b",
        r"\bwho are you\b",
        r"\bkaise ho\b",
        r"\bkya haal\b",
    ]

    if any(re.search(pattern, msg) for pattern in small_talk_patterns):
        return (
            " I am your SGU admission counselor assistant. "
            "Tell me what specific information you want, and I will guide you clearly."
        )

    return None


def is_admission_intent_query(user_message):
    """Check if query appears related to SGU admission counseling."""
    msg = (user_message or "").lower()
    if not msg:
        return False

    domain_keywords = {
        "sgu", "admission", "apply", "application", "fee", "fees", "eligibility", "criteria",
        "process", "procedure", "steps", "step",
        "hostel", "placement", "recruiter", "scholarship", "document", "deadline", "course",
        "courses", "department", "departments", "program", "programs", "college", "university",
        "offer", "offers", "provide", "provides", "available", "stream", "streams", "branch", "branches",
        "syllabus", "curriculum", "subject", "subjects", "semester", "semesters", "module", "modules",
        "taught", "teach", "teaching", "study", "studies", "learn", "learning", "topics",
        "engineering", "engineer", "aeronautical", "aeronotical", "aerotical", "mechanical", "civil", "ece",
        "architecture", "law", "communication", "media", "management", "bba", "mca",
        "btech", "mba", "bca", "cse", "aiml", "ai", "ml",
        "entrance", "counseling", "counselling", "campus", "contact", "office", "timings"
    }

    course_detail_patterns = [
        r"what\s+will\s+be\s+taught",
        r"what\s+is\s+taught",
        r"kya\s+padhaya",
        r"kya\s+sikhaya",
        r"course\s+details",
        r"subject[s]?\s+in",
        r"syllabus\s+of",
        r"curriculum\s+of",
    ]

    if any(re.search(pattern, msg) for pattern in course_detail_patterns):
        return True

    raw_tokens = set(re.findall(r"[a-zA-Z]+", msg))

    # Basic singularization helps map plural user words like "courses" -> "course".
    normalized_tokens = set()
    for token in raw_tokens:
        normalized_tokens.add(token)
        if token.endswith("ies") and len(token) > 4:
            normalized_tokens.add(token[:-3] + "y")
        if token.endswith("es") and len(token) > 3:
            normalized_tokens.add(token[:-2])
        if token.endswith("s") and len(token) > 3:
            normalized_tokens.add(token[:-1])

    # Common misspellings seen in student queries.
    typo_aliases = {
        "aeronotical": "aeronautical",
        "aerotical": "aeronautical",
        "aeronautic": "aeronautical",
        "mechnical": "mechanical",
        "mecanical": "mechanical",
        "civill": "civil",
        "managment": "management",
        "mangement": "management",
        "mbaa": "mba",
        "bbba": "bba",
        "machanical": "mechanical",
        "archetecture": "architecture",
        "archtecture": "architecture",
        "syallabus": "syllabus",
        "silabus": "syllabus",
        "eligiblity": "eligibility",
        "eligibilty": "eligibility",
        "documants": "documents",
        "admision": "admission",
        "cource": "course",
        "coures": "course",
        "enginering": "engineering",
        "enginnering": "engineering",
    }

    normalized_tokens.update(typo_aliases.get(t, t) for t in list(normalized_tokens))

    if len(normalized_tokens.intersection(domain_keywords)) > 0:
        return True

    # Generic fuzzy typo handling for unseen misspellings (all courses/domains).
    fuzzy_terms = {
        "admission", "eligibility", "course", "courses", "department", "program",
        "fees", "syllabus", "curriculum", "subject", "subjects", "placements",
        "engineering", "mechanical", "civil", "aeronautical", "management",
        "architecture", "law", "communication", "btech", "bca", "mca", "mba", "bba",
        "cse", "aiml", "documents", "hostel", "scholarship", "entrance", "process",
    }

    for token in normalized_tokens:
        if len(token) < 4:
            continue
        if difflib.get_close_matches(token, fuzzy_terms, n=1, cutoff=0.82):
            return True

    return False


def _normalize_tokens(text):
    stop_words = {
        "what", "tell", "about", "please", "more", "with", "from", "that", "this", "have",
        "how", "much", "for", "the", "and", "are", "you", "can", "give", "me", "all",
        "any", "into", "your", "our", "they", "them", "than", "then", "when", "where"
    }
    return {
        token for token in re.findall(r"[a-zA-Z]+", (text or "").lower())
        if len(token) > 2 and token not in stop_words
    }


def _extract_top_context_lines(question, context, max_lines=3):
    """Pick the most relevant context lines for the user's question."""
    cleaned_context = (context or "").strip()
    if not cleaned_context or cleaned_context == "General admission information available.":
        return []

    # build_context appends fallback text; exclude that for precision.
    cleaned_context = cleaned_context.replace("\nFallback:", ". ")

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", cleaned_context)
        if s.strip()
    ]
    if not sentences:
        return []

    question_l = (question or "").lower()
    query_terms = _normalize_tokens(question)

    intent_keywords = {
        "fees": {"fee", "fees", "tuition", "cost", "price", "charges", "inr", "rs", "rupee"},
        "admission": {"admission", "apply", "application", "documents", "deadline", "process", "counseling", "counselling", "entrance"},
        "eligibility": {"eligibility", "criteria", "minimum", "marks", "qualification", "required"},
        "placement": {"placement", "recruiters", "internship", "package", "career"},
        "hostel": {"hostel", "mess", "food", "accommodation", "room"},
        "scholarship": {"scholarship", "financial", "aid", "waiver", "discount"},
        "contact": {"contact", "phone", "email", "office", "timings", "location"},
    }

    active_intents = []
    for intent, words in intent_keywords.items():
        if any(word in question_l for word in words):
            active_intents.append(intent)

    scored = []
    for sent in sentences:
        sent_l = sent.lower()
        sent_terms = _normalize_tokens(sent_l)
        overlap = len(query_terms.intersection(sent_terms))

        intent_boost = 0
        for intent in active_intents:
            if any(w in sent_l for w in intent_keywords[intent]):
                intent_boost += 3

        # Avoid picking random numeric lines when there is no semantic overlap.
        numeric_boost = 1 if (overlap > 0 and re.search(r"\d", sent_l)) else 0
        score = (overlap * 2) + intent_boost + numeric_boost

        scored.append((score, sent))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [s for score, s in scored if score > 0][:max_lines]

    return selected


def build_rag_fallback_response(question, context, llm_error):
    """Return a useful response even when the LLM is unavailable."""
    _ = llm_error  # Keep arg for logging path compatibility.

    top_lines = _extract_top_context_lines(question, context, max_lines=4)
    if top_lines:
        joined = " ".join(top_lines)
        return (
            "Based on SGU information, here is what I can confirm right now: " + joined
        )

    reprompts = [
        "Pardon, I did not catch that clearly. Could you repeat your question?",
        "Could you please repeat that once?",
        "Tell me the specific detail you want, for example fees, eligibility, syllabus, or placements.",
        "I missed that. Please ask again in a short and clear line.",
    ]
    return random.choice(reprompts)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'SGU Admission Counselor API is running',
        'version': '1.0.0'
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint - receives user message, returns AI response"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'Missing message field'}), 400
        
        user_message = data['message'].strip()
        session_id = data.get('session_id')  # Optional session tracking
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        # For simple greetings/small-talk, avoid RAG/LLM and answer directly.
        rule_response = build_rule_based_response(user_message)
        if rule_response:
            response_data = {
                'response': rule_response,
                'source': 'rules',
                'message': user_message
            }
            if session_id and chat_history_manager:
                chat_history_manager.add_message(session_id, 'user', user_message)
                chat_history_manager.add_message(session_id, 'assistant', rule_response, 
                                                metadata={'source': 'rules'})
                response_data['session_id'] = session_id
            return jsonify(response_data)

        # If user query is not admission-related, guide them clearly instead of random KB snippets.
        if not is_admission_intent_query(user_message):
            fallback_msg = (
                "I can help with SGU admission-related questions only. "
                "Please ask about admission process, fees, eligibility, placements, hostel, scholarships, or documents."
            )
            response_data = {
                'response': fallback_msg,
                'source': 'rules',
                'message': user_message
            }
            if session_id and chat_history_manager:
                chat_history_manager.add_message(session_id, 'user', user_message)
                chat_history_manager.add_message(session_id, 'assistant', fallback_msg, 
                                                metadata={'source': 'rules'})
                response_data['session_id'] = session_id
            return jsonify(response_data)

        # Prefer deterministic branch details for aeronautical queries.
        branch_response = build_targeted_branch_response(user_message)
        if branch_response:
            response_data = {
                'response': branch_response,
                'source': 'branch_context',
                'message': user_message
            }
            if session_id and chat_history_manager:
                chat_history_manager.add_message(session_id, 'user', user_message)
                chat_history_manager.add_message(session_id, 'assistant', branch_response, 
                                                metadata={'source': 'branch_context'})
                response_data['session_id'] = session_id
            return jsonify(response_data)

        # Deterministic response for department/program catalog questions.
        catalog_response = build_catalog_response(user_message)
        if catalog_response:
            response_data = {
                'response': catalog_response,
                'source': 'catalog',
                'message': user_message
            }
            if session_id and chat_history_manager:
                chat_history_manager.add_message(session_id, 'user', user_message)
                chat_history_manager.add_message(session_id, 'assistant', catalog_response, 
                                                metadata={'source': 'catalog'})
                response_data['session_id'] = session_id
            return jsonify(response_data)
        
        # Check cache first
        cached_response = get_cached_response(user_message)
        if cached_response:
            response_data = {
                'response': cached_response,
                'source': 'cache',
                'message': user_message
            }
            if session_id and chat_history_manager:
                chat_history_manager.add_message(session_id, 'user', user_message)
                chat_history_manager.add_message(session_id, 'assistant', cached_response, 
                                                metadata={'source': 'cache'})
                response_data['session_id'] = session_id
            return jsonify(response_data)
        
        # Get RAG context
        context = get_rag_context(user_message)
        
        # Build prompt
        prompt = build_prompt(user_message, context)

        # Keep API available even when API key is missing/invalid.
        if not LLM_ENABLED or client is None:
            ai_response = build_rag_fallback_response(user_message, context, "LLM disabled")
            cache_response(user_message, ai_response)
            response_data = {
                'response': ai_response,
                'source': 'rag_fallback',
                'message': user_message
            }
            if session_id and chat_history_manager:
                chat_history_manager.add_message(session_id, 'user', user_message)
                chat_history_manager.add_message(session_id, 'assistant', ai_response, 
                                                metadata={'source': 'rag_fallback'})
                response_data['session_id'] = session_id
            return jsonify(response_data)
        
        # Get AI response with retries and optional model fallback.
        response = None
        last_llm_error = None
        response_source = 'generated'
        model_candidates = [MODEL_NAME]
        if FALLBACK_MODEL_NAME and FALLBACK_MODEL_NAME != MODEL_NAME:
            model_candidates.append(FALLBACK_MODEL_NAME)

        for model_name in model_candidates:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"temperature": 0.5, "max_output_tokens": 1000},
                    )
                    break
                except Exception as llm_error:
                    last_llm_error = llm_error
                    if attempt == 0:
                        time.sleep(1)
            if response is not None:
                break

        ai_response = ((response.text or "").strip() if response else "")
        
        if not ai_response:
            if last_llm_error is not None:
                print(f"⚠️ LLM temporary failure: {last_llm_error}")
                ai_response = build_rag_fallback_response(user_message, context, last_llm_error)
                response_source = 'rag_fallback'
            else:
                ai_response = "I didn't quite catch that. Could you repeat?"
        else:
            # Cache this response
            cache_response(user_message, ai_response)
        
        response_data = {
            'response': ai_response,
            'source': response_source,
            'message': user_message
        }
        
        # Save to chat history
        if session_id and chat_history_manager:
            chat_history_manager.add_message(session_id, 'user', user_message)
            chat_history_manager.add_message(session_id, 'assistant', ai_response, 
                                            metadata={'source': response_source})
            response_data['session_id'] = session_id
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"❌ Error in /api/chat: {e}")
        return jsonify({
            'error': str(e),
            'response': 'I am having trouble at the moment. Please try again.'
        }), 500


@app.route('/api/init', methods=['GET'])
def initialize():
    """Initialize services endpoint"""
    try:
        init_services()
        return jsonify({
            'status': 'ok',
            'message': 'Services initialized successfully'
        })
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to initialize services'
        }), 500


@app.route('/api/models', methods=['GET'])
def models():
    """Get available models info"""
    return jsonify({
        'model': MODEL_NAME,
        'embedding_model': 'all-MiniLM-L6-v2',
        'tts_voice': 'en-IN-NeerjaNeural',
        'rag_enabled': retriever is not None
    })


# Chat History Endpoints
@app.route('/api/chat-history/new', methods=['POST'])
def create_session():
    """Create a new chat session"""
    try:
        if not chat_history_manager:
            return jsonify({'error': 'Chat history service not available'}), 500
        
        session_id = chat_history_manager.create_session()
        return jsonify({
            'session_id': session_id,
            'status': 'created'
        }), 201
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat-history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    """Get all messages from a chat session"""
    try:
        if not chat_history_manager:
            return jsonify({'error': 'Chat history service not available'}), 500
        
        messages = chat_history_manager.get_session_messages(session_id)
        session_info = chat_history_manager.get_session_info(session_id)
        
        if session_info is None:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'session_id': session_id,
            'messages': messages,
            'started_at': session_info['started_at'],
            'updated_at': session_info['updated_at'],
            'message_count': session_info['message_count']
        })
    except Exception as e:
        print(f"❌ Error retrieving chat history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat-history/sessions', methods=['GET'])
def list_chat_sessions():
    """List all chat sessions (most recent first)"""
    try:
        if not chat_history_manager:
            return jsonify({'error': 'Chat history service not available'}), 500
        
        limit = request.args.get('limit', 10, type=int)
        sessions = chat_history_manager.list_sessions(limit=limit)
        
        return jsonify({
            'sessions': sessions,
            'total': len(sessions)
        })
    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat-history/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """Delete an entire chat session"""
    try:
        if not chat_history_manager:
            return jsonify({'error': 'Chat history service not available'}), 500
        
        success = chat_history_manager.delete_session(session_id)
        
        if not success:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'session_id': session_id,
            'status': 'deleted'
        })
    except Exception as e:
        print(f"❌ Error deleting session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat-history/<session_id>/clear', methods=['POST'])
def clear_chat_session(session_id):
    """Clear all messages from a session (keep session metadata)"""
    try:
        if not chat_history_manager:
            return jsonify({'error': 'Chat history service not available'}), 500
        
        success = chat_history_manager.clear_session(session_id)
        
        if not success:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'session_id': session_id,
            'status': 'cleared'
        })
    except Exception as e:
        print(f"❌ Error clearing session: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n🎓 SGU Admission Counselor - API Server")
    print("=" * 50)
    
    # Initialize services on startup
    init_services()
    
    print("\n🚀 Starting Flask API server...")
    print("📡 API running at http://localhost:5000")
    print("🔌 CORS enabled for React frontend at http://localhost:3000")
    print("\nAPI Endpoints:")
    print("  GET  /api/health                  - Health check")
    print("  POST /api/chat                    - Send message, get response")
    print("  GET  /api/init                    - Initialize services")
    print("  GET  /api/models                  - Get model info")
    print("\nChat History Endpoints:")
    print("  POST /api/chat-history/new        - Create new session")
    print("  GET  /api/chat-history/<id>       - Get session messages")
    print("  GET  /api/chat-history/sessions   - List all sessions")
    print("  DELETE /api/chat-history/<id>     - Delete session")
    print("  POST /api/chat-history/<id>/clear - Clear messages")
    print("\n" + "=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
