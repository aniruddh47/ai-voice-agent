import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai

from backend.utils import (
    SemanticCache,
    EmbeddingService,
    SemanticRetriever,
    load_and_chunk_knowledge
)

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
CACHE_PATH = os.path.join(BASE_DIR, "backend", "cache", "cache.json")

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", "0.15"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "1600"))
CACHE_THRESHOLD = float(os.getenv("CACHE_THRESHOLD", "0.90"))
DEBUG = os.getenv("RAG_DEBUG", "1") == "1"

client = genai.Client(api_key=API_KEY)

# Global services
embeddings_service = None
retriever = None
cache = None


def init_services():
    """Initialize RAG and embedding services"""
    global embeddings_service, retriever, cache
    
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
        print("✅ RAG services ready")
    except Exception as e:
        print(f"⚠️ Service initialization failed: {e}")


def get_rag_context(question):
    """Get RAG context for the question"""
    if retriever is None:
        return "General admission information available."
    
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
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        # Check cache first
        cached_response = get_cached_response(user_message)
        if cached_response:
            return jsonify({
                'response': cached_response,
                'source': 'cache',
                'message': user_message
            })
        
        # Get RAG context
        context = get_rag_context(user_message)
        
        # Build prompt
        prompt = build_prompt(user_message, context)
        
        # Get AI response
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={"temperature": 0.5, "max_output_tokens": 1000},
        )
        
        ai_response = (response.text or "").strip()
        
        if not ai_response:
            ai_response = "I didn't quite catch that. Could you repeat?"
        else:
            # Cache this response
            cache_response(user_message, ai_response)
        
        return jsonify({
            'response': ai_response,
            'source': 'generated',
            'message': user_message
        })
    
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


if __name__ == '__main__':
    print("\n🎓 SGU Admission Counselor - API Server")
    print("=" * 50)
    
    # Initialize services on startup
    init_services()
    
    print("\n🚀 Starting Flask API server...")
    print("📡 API running at http://localhost:5000")
    print("🔌 CORS enabled for React frontend at http://localhost:3000")
    print("\nAPI Endpoints:")
    print("  GET  /api/health      - Health check")
    print("  POST /api/chat        - Send message, get response")
    print("  GET  /api/init        - Initialize services")
    print("  GET  /api/models      - Get model info")
    print("\n" + "=" * 50 + "\n")
    
    app.run(host='127.0.0.1', port=5000, debug=False)
