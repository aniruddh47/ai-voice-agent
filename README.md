# 🎓 SGU Admission Counselor - AI Voice Assistant

A production-ready AI voice assistant for Sanjay Ghodawat University (SGU) admission counseling. Features real-time voice I/O, intelligent RAG-based responses, semantic caching, and a modern React frontend.

## 📁 Project Structure

```
admission-counselling/
├── backend/                          # Python Flask backend
│   ├── main.py                      # Standalone voice assistant (CLI mode)
│   ├── api_server.py                # Flask REST API server
│   ├── requirements.txt             # Python dependencies
│   ├── utils/                       # Core utilities
│   │   ├── cache.py                # Semantic caching system
│   │   ├── embeddings.py           # Embedding service (SentenceTransformers)
│   │   ├── retrieval.py            # RAG retrieval system
│   │   ├── chunking.py             # Knowledge base chunking
│   │   ├── voice.py                # Voice utilities
│   │   └── __init__.py
│   ├── data/                        # Knowledge base (JSON)
│   │   ├── college_info.json
│   │   ├── admission_procedures.json
│   │   ├── departments_info.json
│   │   └── facilities_detailed.json
│   ├── cache/                       # Runtime cache directory
│   │   ├── cache.json              # Semantic cache storage
│   │   └── semantic_cache.json
│   ├── models/                      # ML models
│   │   └── vosk-model-small-en-in-0.4/  # Speech recognition model
│   ├── tests/                       # Test and experimental files
│   │   ├── test.py
│   │   ├── test2.py
│   │   └── ai_agent.py
│   └── __init__.py
│
├── frontend/                        # React + Vite + Tailwind frontend
│   ├── src/
│   │   ├── App.jsx                 # Main app component
│   │   ├── main.jsx                # Entry point
│   │   ├── index.css               # Global styles
│   │   ├── components/             # Reusable components
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── VoicePanel.jsx
│   │   │   ├── CallControls.jsx
│   │   │   └── LoadingScreen.jsx
│   │   └── pages/                  # Page components
│   ├── index.html                  # HTML template
│   ├── package.json                # NPM dependencies
│   ├── vite.config.js              # Vite configuration
│   ├── tailwind.config.js          # Tailwind CSS config
│   ├── postcss.config.js           # PostCSS config
│   └── node_modules/               # Installed packages
│
├── docs/                           # Documentation
│   ├── README.md                   # Main README
│   ├── QUICK_START.md              # Quick start guide
│   ├── INTEGRATION.md              # Integration details
│   └── SYSTEM_DIAGRAM.txt          # Architecture diagram
│
├── scripts/                        # Startup and utility scripts
│   ├── START.bat                   # Windows batch starter
│   └── START.ps1                   # PowerShell starter
│
├── .env                            # Environment variables (NOT in git)
├── .gitignore                      # Git ignore rules
└── .git/                           # Git repository

```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 16+
- pip and npm installed

### 1. Backend Setup

```bash
# Navigate to root
cd "d:\admission-counselling"

# Create Python virtual environment
python -m venv .venv

# Activate environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Set up .env
copy .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Run Backend Server

```bash
# From root (with .venv activated)
python api_server.py
```

### 4. Access the Application

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:5000`

## 🔧 Configuration

Environment variables in `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
WHISPER_MODEL_SIZE=small.en
TTS_VOICE=en-US-Female
RAG_TOP_K=3
RAG_THRESHOLD=0.15
MAX_CONTEXT_CHARS=1600
CACHE_THRESHOLD=0.90
DEBUG=1
```

## 📊 Technology Stack

**Backend:**
- Python 3.11
- Flask + Flask-CORS
- Google Gemini API
- SentenceTransformers (embeddings)
- Faster Whisper (speech recognition)
- Edge TTS (text-to-speech)

**Frontend:**
- React 18
- Vite
- Tailwind CSS 3.4
- Web Speech API
- Web SpeechSynthesis API

## ✨ Features

- ✅ Real-time voice input (Web Speech API)
- ✅ Professional AI responses (Gemini LLM)
- ✅ Semantic caching for fast responses
- ✅ RAG system with knowledge base
- ✅ Text-to-speech output (consistent voice)
- ✅ Beautiful, responsive UI
- ✅ RESTful API architecture
- ✅ Error handling and fallbacks

## 📝 Development

### Backend Development
```bash
# Run main CLI version (testing)
python backend/main.py

# Or use Flask API
python api_server.py
```

### Frontend Development
```bash
cd frontend
npm run dev      # Development server
npm run build    # Production build
npm run preview  # Preview build
```

## 🐛 Troubleshooting

**GEMINI_API_KEY not found:**
- Create `.env` file in root
- Add your API key: `GEMINI_API_KEY=xxx`

**Port 5000/5173 already in use:**
- Change port in `api_server.py` or `vite.config.js`

**Voice not playing:**
- Check browser permissions for audio/microphone
- Ensure backend is running and API is accessible

**Models not loading:**
- Check `backend/models/` directory exists
- Ensure proper file paths in code

## 📄 License

Internal use for SGU admission counseling

## 👤 Support

For issues or questions, check the docs/ folder or contact the development team.

---

**Last Updated:** April 7, 2026
**Project Status:** Production Ready ✅
