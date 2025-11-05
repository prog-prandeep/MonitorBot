"""Session management module for Instagram cookies"""
import json
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger("ig_monitor_bot")

class SessionManager:
    """Manages Instagram session rotation"""
    
    # Hardcoded fallback session (last resort)
    FALLBACK_SESSION = ""
    
    def __init__(self, session_file="session.json"):
        self.session_file = session_file
        self.sessions = []
        self.current_index = 0
        self.current_session = None
        self.load_sessions()
    
    def load_sessions(self):
        """Load sessions from file"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", [])
                    if self.sessions:
                        self.current_session = self.sessions[0]
                        logger.info(f"✅ Loaded {len(self.sessions)} sessions")
                    else:
                        logger.warning("⚠️ No sessions in file, using fallback")
                        self.current_session = self.FALLBACK_SESSION
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                self.sessions = []
                self.current_session = self.FALLBACK_SESSION
        else:
            logger.warning(f"⚠️ {self.session_file} not found, using fallback session")
            self.sessions = []
            self.current_session = self.FALLBACK_SESSION
    
    def save_sessions(self):
        """Save sessions to file"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump({"sessions": self.sessions}, f, indent=2)
            logger.info(f"💾 Saved {len(self.sessions)} sessions")
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")
    
    def get_current_session(self) -> str:
        """Get current active session"""
        return self.current_session
    
    def rotate_session(self):
        """Switch to next session on error"""
        if not self.sessions:
            logger.warning("⚠️ No sessions available, using fallback")
            self.current_session = self.FALLBACK_SESSION
            return self.current_session
        
        # Move to next session
        self.current_index = (self.current_index + 1) % len(self.sessions)
        self.current_session = self.sessions[self.current_index]
        
        logger.info(f"🔄 Rotated to session {self.current_index + 1}/{len(self.sessions)}")
        
        # If we've cycled through all, use fallback
        if self.current_index == 0:
            logger.warning("⚠️ All sessions failed, using fallback")
            self.current_session = self.FALLBACK_SESSION
        
        return self.current_session
    
    def add_session(self, sessionid: str) -> bool:
        """Add new session"""
        if sessionid in self.sessions:
            logger.warning(f"⚠️ Session already exists")
            return False
        
        self.sessions.append(sessionid)
        self.save_sessions()
        
        # If this is the first session, set it as current
        if len(self.sessions) == 1:
            self.current_session = sessionid
            self.current_index = 0
        
        logger.info(f"✅ Added new session (total: {len(self.sessions)})")
        return True
    
    def remove_session(self, sessionid: str) -> bool:
        """Remove session by ID or by prefix.

        If the provided sessionid matches multiple sessions as a prefix, the remove is aborted
        and a warning is logged to avoid accidental deletions. A full session id still works.
        """
        # Find matches by exact or prefix match
        matches = [s for s in self.sessions if s == sessionid or s.startswith(sessionid)]
        if not matches:
            logger.warning("⚠️ Session not found")
            return False

        if len(matches) > 1:
            logger.warning(f"⚠️ Ambiguous prefix: {len(matches)} sessions match. Be more specific.")
            return False

        found = matches[0]
        # Remember index before removal to adjust rotation state correctly
        try:
            idx = self.sessions.index(found)
        except ValueError:
            logger.warning("⚠️ Session not found during removal")
            return False

        # Remove session
        self.sessions.pop(idx)
        self.save_sessions()

        # Adjust current_index/current_session
        if not self.sessions:
            self.current_index = 0
            self.current_session = self.FALLBACK_SESSION
        else:
            # If removed session was before the current index, shift current_index left
            if idx < self.current_index:
                self.current_index -= 1
            # If removed was the current, point to the session at the same index (or wrap)
            if self.current_session == found:
                # clamp index to valid range
                self.current_index = self.current_index % len(self.sessions)
                self.current_session = self.sessions[self.current_index]

        logger.info(f"🗑️ Removed session (remaining: {len(self.sessions)})")
        return True
    
    def get_session_count(self) -> int:
        """Get total number of sessions"""
        return len(self.sessions)
    
    def get_all_sessions(self) -> list:
        """Get all session IDs (masked for security)"""
        return [f"{s[:10]}...{s[-10:]}" if len(s) > 20 else s for s in self.sessions]
    
    def reset_rotation(self):
        """Reset to first session"""
        if self.sessions:
            self.current_index = 0
            self.current_session = self.sessions[0]
            logger.info("🔄 Reset to first session")