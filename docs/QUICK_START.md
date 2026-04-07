# 🚀 Quick Start Guide - Connected AI Chatbot

This guide shows how to run the complete system with Python backend + React frontend.

## Prerequisites

- ✅ Python 3.11+ with venv activated
- ✅ Node.js 16+ installed
- ✅ All Python dependencies installed (from previous setup)
- ✅ Flask & flask-cors installed (just installed)

## System Architecture

```
┌─────────────────────────────────────────┐
│      React Frontend (Port 3000)          │
│   - Chat UI with voice assistant        │
│   - Real-time message display           │
│   - Microphone simulation               │
└────────────────┬────────────────────────┘
                 │
              HTTP API
             (JSON/REST)
                 │
┌────────────────▼────────────────────────┐
│    Flask API Server (Port 5000)         │
│   - /api/chat endpoint                  │
│   - RAG retrieval                       │
│   - Gemini LLM integration              │
│   - Semantic cache                      │
└────────────────┬────────────────────────┘
                 │
        ┌────────┼──────────┐
        │        │          │
    RAG DB   Cache   Models
    (JSON)   (JSON)  (Whisper)
```

## Step 1: Start Python API Server

**Terminal 1 (Python):**

```bash
cd d:\admisson\ councelling

# Activate venv (if not already)
.\.venv\Scripts\Activate.ps1

# Run API server
python api_server.py
```

**Expected Output:**
```
🎓 SGU Admission Counselor - API Server
==================================================

⏳ Initializing RAG services...
✅ RAG services ready
🚀 Starting Flask API server...
📡 API running at http://localhost:5000
🔌 CORS enabled for React frontend at http://localhost:3000

API Endpoints:
  GET  /api/health      - Health check
  POST /api/chat        - Send message, get response
  GET  /api/init        - Initialize services
  GET  /api/models      - Get model info

==================================================
```

✅ **Server is ready when you see this message**

---

## Step 2: Start React Frontend

**Terminal 2 (Node.js):**

```bash
cd d:\admisson\ councelling\chat-ui

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

**Expected Output:**
```
Local:        http://localhost:3000/
Ready in 123ms
```

✅ **Frontend is ready when you see this**

---

## Step 3: Use the App

1. **Open browser** → `http://localhost:3000`
2. **Wait for loading screen** (2 seconds)
3. **Click "Start Call"** button (green)
4. **Click microphone button** to ask questions
5. **Watch chat display real responses** from your Python backend!

---

## Testing the Connection

### Test 1: API Health Check
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "message": "SGU Admission Counselor API is running",
  "version": "1.0.0"
}
```

### Test 2: Send Chat Message
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Tell me about your programs\"}"
```

Expected response:
```json
{
  "response": "Absolutely! So, SGU offers a wide range...",
  "source": "generated",
  "message": "Tell me about your programs"
}
```

---

## Troubleshooting

### ❌ "API Server not connected" warning in UI

**Solution:** Make sure `api_server.py` is running in Terminal 1

```bash
python api_server.py
```

### ❌ "Cannot find module" error in Flask

**Solution:** Install missing dependencies

```bash
pip install flask flask-cors
```

### ❌ Port already in use (5000 or 3000)

**Solution:** Kill existing process or change port

```bash
# For Python (5000)
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# For Node (3000)
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### ❌ React build fails

**Solution:** Clear cache and reinstall

```bash
cd chat-ui
rm -r node_modules
npm install
npm run dev
```

### ❌ CORS error in browser console

**Solution:** Make sure Flask is started with the API server. Check console output shows:
```
🔌 CORS enabled for React frontend at http://localhost:3000
```

---

## Understanding the Flow

### When User Types/Speaks:

1. **Frontend** → Sends message via `POST /api/chat` with JSON body
2. **Backend** → Receives message, processes:
   - ✅ Checks semantic cache first (fast response)
   - ✅ Retrieves relevant context using RAG
   - ✅ Builds prompt with context
   - ✅ Calls Gemini API for response
   - ✅ Caches response for next time
3. **Backend** → Returns response JSON with `response` field
4. **Frontend** → Displays AI message in chat bubble
5. **TTS** → Speaks the response (future integration)

---

## API Endpoints

### `GET /api/health`
Health check - verify server is running

```bash
curl http://localhost:5000/api/health
```

### `POST /api/chat`
Main chat endpoint

**Request:**
```json
{
  "message": "Tell me about your college"
}
```

**Response (Cache Hit):**
```json
{
  "response": "Absolutely! SGU is a premier...",
  "source": "cache",
  "message": "Tell me about your college"
}
```

**Response (Generated):**
```json
{
  "response": "Absolutely! SGU is a premier...",
  "source": "generated",
  "message": "Tell me about your college"
}
```

### `GET /api/init`
Reinitialize RAG services

```bash
curl http://localhost:5000/api/init
```

### `GET /api/models`
Get model information

```bash
curl http://localhost:5000/api/models
```

---

## Development Tips

### Change API Timeout
In `chat-ui/src/App.jsx`, modify fetch timeout:
```javascript
const response = await fetch(`${API_BASE_URL}/api/chat`, {
  signal: AbortSignal.timeout(30000) // 30 seconds
})
```

### Add Logging
In `api_server.py`, enable debug mode:
```python
app.run(host='127.0.0.1', port=5000, debug=True)  # ← Set to True
```

### Test Different Messages
Edit test questions in `api_server.py`:
```python
# Add your own test messages here
test_messages = [
  "Your custom question..."
]
```

### Build for Production
```bash
cd chat-ui
npm run build
# Outputs to chat-ui/dist/
```

---

## Next Steps

### 1. Add Real Voice Input
Replace simulated listening with actual microphone input:
```javascript
const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
// Process audio → send to backend STT
```

### 2. Add Text Input
Add input field for users to type messages directly:
```jsx
<input 
  type="text" 
  placeholder="Type a message..."
  onKeyPress={(e) => e.key === 'Enter' && sendMessage(e.target.value)}
/>
```

### 3. Add TTS Audio Playback
Stream audio from backend TTS service:
```javascript
const audio = new Audio(`data:audio/mp3;base64,${response.audio}`)
audio.play()
```

### 4. Deploy to Production
- Build React: `npm run build`
- Host Flask on gunicorn
- Serve React from Flask static files

---

## File Structure

```
d:\admisson councelling\
├── main.py                    # Original voice assistant
├── api_server.py             # ← NEW: Flask API wrapper
├── cache.py, chunking.py, etc.
└── chat-ui/
    ├── src/
    │   ├── App.jsx          # ← UPDATED: Now connects to API
    │   ├── components/
    │   │   ├── ChatInterface.jsx
    │   │   ├── VoicePanel.jsx
    │   │   ├── CallControls.jsx
    │   │   └── LoadingScreen.jsx
    │   └── main.jsx
    ├── package.json
    ├── vite.config.js
    └── README.md
```

---

## Support

For issues or questions:
1. Check terminal output for error messages
2. Verify both servers are running (ports 5000 + 3000)
3. Clear browser cache and reload
4. Check Flask debug logs: `debug=True` in `api_server.py`

---

**Happy chatting! 🎉**
