"""
Chat history persistence manager.
Stores and retrieves conversation histories from JSON files.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid


class ChatHistoryManager:
    """Manages persistent chat history storage."""

    def __init__(self, cache_dir: str = None):
        """
        Initialize the chat history manager.
        
        Args:
            cache_dir: Directory to store chat history files. 
                      Defaults to backend/cache/
        """
        if cache_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base_dir, "cache")
        
        self.cache_dir = cache_dir
        self.history_file = os.path.join(cache_dir, "chat_history.json")
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize history file if it doesn't exist
        if not os.path.exists(self.history_file):
            self._save_all_history({"sessions": {}})

    def _load_all_history(self) -> Dict:
        """Load all chat history from file."""
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"sessions": {}}

    def _save_all_history(self, data: Dict) -> None:
        """Save all chat history to file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Failed to save chat history: {e}")

    def create_session(self) -> str:
        """
        Create a new chat session.
        
        Returns:
            Session ID (UUID)
        """
        session_id = str(uuid.uuid4())
        history = self._load_all_history()
        
        history["sessions"][session_id] = {
            "id": session_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "messages": []
        }
        
        self._save_all_history(history)
        return session_id

    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a message to a chat session.
        
        Args:
            session_id: Session ID
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata (source, processing_time, etc.)
        """
        history = self._load_all_history()
        
        if session_id not in history["sessions"]:
            print(f"⚠️ Session {session_id} not found, creating new one")
            history["sessions"][session_id] = {
                "id": session_id,
                "started_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "messages": []
            }
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if metadata:
            message["metadata"] = metadata
        
        history["sessions"][session_id]["messages"].append(message)
        history["sessions"][session_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        self._save_all_history(history)

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """
        Get all messages from a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of message dictionaries
        """
        history = self._load_all_history()
        
        if session_id not in history["sessions"]:
            return []
        
        return history["sessions"][session_id].get("messages", [])

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        Get session metadata (creation time, message count, etc.)
        
        Args:
            session_id: Session ID
            
        Returns:
            Session info dict or None if not found
        """
        history = self._load_all_history()
        
        if session_id not in history["sessions"]:
            return None
        
        session = history["sessions"][session_id]
        return {
            "id": session["id"],
            "started_at": session["started_at"],
            "updated_at": session["updated_at"],
            "message_count": len(session["messages"])
        }

    def list_sessions(self, limit: int = 10) -> List[Dict]:
        """
        List all chat sessions (most recent first).
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session info dicts
        """
        history = self._load_all_history()
        
        sessions = list(history["sessions"].values())
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return [
            {
                "id": s["id"],
                "started_at": s["started_at"],
                "updated_at": s["updated_at"],
                "message_count": len(s["messages"])
            }
            for s in sessions[:limit]
        ]

    def clear_session(self, session_id: str) -> bool:
        """
        Clear all messages from a session (keeps session metadata).
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        history = self._load_all_history()
        
        if session_id not in history["sessions"]:
            return False
        
        history["sessions"][session_id]["messages"] = []
        history["sessions"][session_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_all_history(history)
        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete an entire session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        history = self._load_all_history()
        
        if session_id not in history["sessions"]:
            return False
        
        del history["sessions"][session_id]
        self._save_all_history(history)
        return True

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta
        
        history = self._load_all_history()
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        sessions_to_delete = [
            sid for sid, session in history["sessions"].items()
            if session.get("updated_at", "") < cutoff_date
        ]
        
        for sid in sessions_to_delete:
            del history["sessions"][sid]
        
        if sessions_to_delete:
            self._save_all_history(history)
        
        return len(sessions_to_delete)
