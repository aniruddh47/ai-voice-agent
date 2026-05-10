# Persistent Chat History Implementation

## Overview
Chat history is now persisted to allow users to continue conversations after page refresh.

## Features Implemented

### Backend (Python/Flask)

#### 1. **Chat History Manager** (`backend/utils/chat_history.py`)
- Manages all chat persistence operations
- Stores sessions and messages in `backend/cache/chat_history.json`
- Key methods:
  - `create_session()` - Creates a new chat session with unique ID
  - `add_message()` - Saves user/assistant messages with metadata
  - `get_session_messages()` - Retrieves all messages from a session
  - `get_session_info()` - Gets session metadata
  - `list_sessions()` - Lists all sessions (paginated)
  - `clear_session()` - Clears messages but keeps session
  - `delete_session()` - Fully removes a session
  - `cleanup_old_sessions()` - Removes old sessions (configurable)

#### 2. **Updated API Endpoints** (`api_server.py`)

**Chat Endpoint (Modified):**
- `POST /api/chat` now accepts optional `session_id` parameter
- Automatically saves both user and assistant messages
- Stores metadata like response source (rules, cache, generated, etc.)

**New History Endpoints:**
- `POST /api/chat-history/new` - Create new session
  - Returns: `{ "session_id": "uuid", "status": "created" }`
  
- `GET /api/chat-history/<session_id>` - Get session messages
  - Returns: `{ "session_id", "messages": [...], "started_at", "updated_at", "message_count" }`
  
- `GET /api/chat-history/sessions` - List all sessions
  - Query param: `limit` (default: 10)
  - Returns: `{ "sessions": [...], "total": count }`
  
- `DELETE /api/chat-history/<session_id>` - Delete session
  - Returns: `{ "session_id", "status": "deleted" }`
  
- `POST /api/chat-history/<session_id>/clear` - Clear messages
  - Returns: `{ "session_id", "status": "cleared" }`

### Frontend (React)

#### 1. **Session Management** (`chat-ui/src/App.jsx`)
- New state: `sessionId` for tracking current session
- LocalStorage persistence: `sgu_chat_session_id` key
- Functions:
  - `initializeOrLoadSession()` - Load or create session on app mount
  - Auto-recovers previous session if available

#### 2. **Chat History Loading**
- On app mount:
  1. Check API health
  2. Load or create session
  3. Load previous messages (if session exists)
  4. Display conversation history to user

#### 3. **Message Persistence**
- Every message sent includes `session_id`
- Backend automatically saves to persistent storage
- Frontend doesn't need explicit save calls

#### 4. **UX Changes**
- **Start Call**: No longer clears messages (preserves history)
- **End Call**: Messages are kept (not cleared)
- **Page Refresh**: Previous conversation loads automatically
- **New Session**: User can clear history via new endpoint (future UI feature)

## Data Structure

### Chat History File (`backend/cache/chat_history.json`)
```json
{
  "sessions": {
    "uuid-1234": {
      "id": "uuid-1234",
      "started_at": "2024-04-21T10:30:00Z",
      "updated_at": "2024-04-21T10:45:00Z",
      "messages": [
        {
          "role": "user",
          "content": "Tell me about admission process",
          "timestamp": "2024-04-21T10:30:15Z"
        },
        {
          "role": "assistant",
          "content": "The admission process involves...",
          "timestamp": "2024-04-21T10:30:45Z",
          "metadata": {
            "source": "generated"
          }
        }
      ]
    }
  }
}
```

### LocalStorage
- Key: `sgu_chat_session_id`
- Value: UUID string (e.g., "550e8400-e29b-41d4-a716-446655440000")
- Persists across browser sessions

## Session Flow

```
App Load
  ↓
Check API Health
  ↓
Try to Load Session from LocalStorage
  ├─→ If exists and valid → Load messages from backend
  ├─→ If not found or invalid → Create new session
  └─→ Store session_id in LocalStorage
  ↓
Display conversation history (if any)
  ↓
User sends message (with session_id)
  ↓
Backend saves: user message + AI response
  ↓
Frontend updates display (already in messages array)
```

## Testing

### Manual Testing Steps

1. **Start Conversation**
   ```
   1. Open app
   2. Click "Start Call"
   3. Ask questions (e.g., "What are the fees?")
   4. Note the session ID in browser console
   ```

2. **Verify Persistence**
   ```
   1. Refresh the page (F5)
   2. Wait for app to load
   3. See previous messages restored
   4. Previous session_id should be reused
   ```

3. **Test New Session** (Future UI)
   ```
   1. Clear localStorage: 
      localStorage.removeItem('sgu_chat_session_id')
   2. Refresh page
   3. New session_id should be created
   ```

4. **Check Backend Storage**
   ```
   1. Open backend/cache/chat_history.json
   2. See all sessions with messages
   3. Each message has timestamp and metadata
   ```

5. **API Testing** (with curl)
   ```bash
   # Create session
   curl -X POST http://localhost:5000/api/chat-history/new
   
   # Get messages
   curl http://localhost:5000/api/chat-history/{session_id}
   
   # List all sessions
   curl http://localhost:5000/api/chat-history/sessions?limit=5
   
   # Send chat with session
   curl -X POST http://localhost:5000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello", "session_id": "{session_id}"}'
   ```

## Files Modified

1. **Backend**
   - ✅ Created: `backend/utils/chat_history.py`
   - ✅ Updated: `backend/utils/__init__.py` (added ChatHistoryManager export)
   - ✅ Updated: `api_server.py` (added endpoints, integrated manager)

2. **Frontend**
   - ✅ Updated: `chat-ui/src/App.jsx` (session management, message loading)

3. **Data**
   - ✅ Auto-created: `backend/cache/chat_history.json` (on first run)

## Future Enhancements

1. **Session Management UI**
   - Button to start new session
   - View/manage past sessions
   - Delete individual sessions

2. **Search & Export**
   - Search within chat history
   - Export conversations as text/PDF

3. **Cloud Sync**
   - Sync history to cloud storage
   - Cross-device sync

4. **Analytics**
   - Track frequently asked questions
   - Session duration metrics
   - User engagement tracking

5. **Auto-cleanup**
   - Automatic deletion of old sessions (>30 days)
   - Implement via cleanup_old_sessions()

## Configuration

Edit these in `api_server.py` or pass via environment:

```python
# Chat history manager init (auto)
chat_history_manager = ChatHistoryManager()

# Location can be customized:
chat_history_manager = ChatHistoryManager(cache_dir='/path/to/cache')
```

## Troubleshooting

**Issue**: Chat history not loading on refresh
- **Solution**: 
  1. Check browser console for errors
  2. Verify `backend/cache/chat_history.json` exists
  3. Check API response: `GET /api/chat-history/{session_id}`

**Issue**: Multiple sessions being created
- **Solution**: 
  1. Clear localStorage: `localStorage.clear()`
  2. Check for browser console errors
  3. Ensure API `/api/chat-history/new` works

**Issue**: Old messages not appearing
- **Solution**: 
  1. Check if session ID matches in LocalStorage
  2. Verify chat_history.json has the session
  3. Check message roles are "user" or "assistant"

**Issue**: Out of storage space
- **Solution**: 
  1. Call `cleanup_old_sessions(days=30)` periodically
  2. Implement cleanup scheduler
  3. Monitor cache file size regularly

## Performance Considerations

- Chat history stored in JSON (simple, human-readable)
- For large deployments, consider:
  - SQLite or PostgreSQL for persistence
  - Redis for session caching
  - Pagination for message retrieval
- Current implementation handles ~1000 sessions efficiently
