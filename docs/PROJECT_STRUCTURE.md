# 📁 Project Structure Guide

## Directory Layout

```
admission-counselling/
│
├── 📂 backend/                      # Python Flask Backend
│   ├── main.py                      # Standalone voice assistant (CLI mode)
│   ├── api_server.py                # Flask REST API (port 5000)
│   ├── requirements.txt             # Python dependencies
│   ├── __init__.py
│   │
│   ├── 📂 utils/                    # Core utilities & modules
│   │   ├── cache.py                # Semantic caching system
│   │   ├── embeddings.py           # Embedding service (SentenceTransformers)
│   │   ├── retrieval.py            # RAG retrieval system
│   │   ├── chunking.py             # Knowledge base chunking
│   │   ├── voice.py                # Voice utilities
│   │   └── __init__.py
│   │
│   ├── 📂 data/                     # Knowledge Base (JSON files)
│   │   ├── college_info.json
│   │   ├── admission_procedures.json
│   │   ├── departments_info.json
│   │   └── facilities_detailed.json
│   │
│   ├── 📂 cache/                    # Runtime Cache Directory
│   │   ├── cache.json              # Semantic cache (auto-generated)
│   │   ├── semantic_cache.json     # Backup cache
│   │   └── temp_input.wav          # Temp audio files
│   │
│   ├── 📂 models/                   # ML Models
│   │   └── vosk-model-small-en-in-0.4/
│   │       ├── README
│   │       ├── am/, conf/, graph/   # Model files
│   │       └── ivector/, phones/
│   │
│   └── 📂 tests/                    # Test & Experimental Files
│       ├── test.py
│       ├── test2.py
│       └── ai_agent.py
│
├── 📂 frontend/                     # React + Vite Frontend
│   ├── src/
│   │   ├── App.jsx                 # Main app component
│   │   ├── main.jsx                # Vite entry point
│   │   ├── index.css               # Global styles
│   │   │
│   │   ├── 📂 components/          # Reusable components
│   │   │   ├── ChatInterface.jsx   # Message display
│   │   │   ├── VoicePanel.jsx      # Microphone panel
│   │   │   ├── CallControls.jsx    # Start/End call
│   │   │   └── LoadingScreen.jsx   # Splash screen
│   │   │
│   │   └── 📂 pages/               # Page components (if added)
│   │
│   ├── index.html                  # HTML template
│   ├── package.json                # NPM dependencies
│   ├── vite.config.js              # Vite configuration
│   ├── tailwind.config.js          # Tailwind CSS config
│   ├── postcss.config.js           # PostCSS config
│   ├── node_modules/               # Installed packages (auto)
│   └── README.md                   # Frontend docs
│
├── 📂 docs/                        # Documentation
│   ├── README.md                   # Main documentation
│   ├── QUICK_START.md              # Quick start guide
│   ├── INTEGRATION.md              # Integration guide
│   ├── CONNECTION_SUMMARY.txt      # Connection notes
│   └── SYSTEM_DIAGRAM.txt          # Architecture diagram
│
├── 📂 scripts/                     # Startup Scripts
│   ├── START.bat                   # Windows batch starter
│   └── START.ps1                   # PowerShell starter
│
├── 📂 .venv/                       # Python virtual environment (auto)
│   ├── Scripts/                    # Executables
│   ├── Lib/                        # Installed packages
│   └── pyvenv.cfg
│
├── .env                            # Environment variables (NOT in git)
├── .env.example                    # Example .env file (in git)
├── .gitignore                      # Git ignore rules
├── README.md                       # Root README
└── .git/                           # Git repository


## Key File Purposes

### Backend Core
- **main.py** - Standalone CLI voice assistant (run locally without API)
- **api_server.py** - Flask REST API that wraps the voice assistant
- **backend/utils/*** - Modular utility classes (cache, embeddings, RAG, etc.)

### Frontend Core
- **App.jsx** - State management, voice I/O, API communication
- **ChatInterface.jsx** - Message display and chat bubbles
- **VoicePanel.jsx** - Microphone button and status
- **CallControls.jsx** - Start/End call buttons
- **LoadingScreen.jsx** - 2-second splash screen

### Data & Configuration
- **data/*.json** - Knowledge base for RAG system
- **models/ ** - Speech recognition model files
- **.env** - API keys and configuration
- **requirements.txt** - Python package dependencies
- **package.json** - Node.js package dependencies

### Documentation
- **README.md** - This main reference
- **QUICK_START.md** - Get started in 5 minutes
- **INTEGRATION.md** - Integration details
- **docs/** - Additional documentation


## Important Notes

### What's NOT in Git
- `.venv/` - Virtual environment (regenerate with `python -m venv .venv`)
- `frontend/node_modules/` - NPM packages (regenerate with `npm install`)
- `.env` - Sensitive data (use `.env.example` as template)
- `__pycache__/` - Cached Python files
- Cache files in `backend/cache/`

### Auto-Generated Directories
- `.venv/` - Created by `python -m venv .venv`
- `node_modules/` - Created by `npm install`
- `__pycache__/` - Created by Python runtime
- `backend/cache/*.json` - Created by semantic cache system

### Running the Project
```bash
# Option 1: Use startup script
scripts/START.bat          # Windows
scripts/START.ps1          # PowerShell

# Option 2: Manual startup
# Terminal 1: Backend
python api_server.py       # Runs on port 5000

# Terminal 2: Frontend
cd frontend
npm run dev                # Runs on port 5173
```

### Adding New Code
- **New backend modules** → `backend/utils/`
- **New React components** → `frontend/src/components/`
- **New pages** → `frontend/src/pages/`
- **New data files** → `backend/data/`
- **New tests** → `backend/tests/`


---
📅 Last Updated: April 7, 2026
✅ Status: Production Ready
