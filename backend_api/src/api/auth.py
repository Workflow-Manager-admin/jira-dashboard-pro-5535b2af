"""
Authentication utilities and session management
Handles JWT tokens, session validation, and security functions
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages user sessions and authentication tokens"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def generate_session_token(self) -> str:
        """Generate a cryptographically secure session token"""
        return secrets.token_urlsafe(32)
    
    def create_session(self, email: str, api_token: str, domain: str, timeout_hours: int = 8) -> str:
        """
        Create a new user session
        
        Args:
            email: User's email address
            api_token: Jira API token (will be hashed for storage)
            domain: Jira domain
            timeout_hours: Session timeout in hours
            
        Returns:
            str: Session token
        """
        session_token = self.generate_session_token()
        
        # Hash the API token for security (don't store plaintext)
        token_hash = hashlib.sha256(api_token.encode()).hexdigest()
        
        session_data = {
            "email": email,
            "api_token": api_token,  # In production, consider additional encryption
            "api_token_hash": token_hash,
            "domain": domain,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=timeout_hours),
            "last_activity": datetime.now()
        }
        
        self.active_sessions[session_token] = session_data
        
        logger.info(f"Session created for user: {email}")
        return session_token
    
    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate session token and return session data
        
        Args:
            token: Session token to validate
            
        Returns:
            Optional[Dict]: Session data if valid, None otherwise
        """
        if not token or token not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[token]
        
        # Check if session has expired
        if datetime.now() > session_data["expires_at"]:
            logger.info(f"Session expired for user: {session_data['email']}")
            self.remove_session(token)
            return None
        
        # Update last activity
        session_data["last_activity"] = datetime.now()
        
        return session_data
    
    def remove_session(self, token: str) -> bool:
        """
        Remove a session
        
        Args:
            token: Session token to remove
            
        Returns:
            bool: True if session was removed, False if not found
        """
        if token in self.active_sessions:
            email = self.active_sessions[token]["email"]
            del self.active_sessions[token]
            logger.info(f"Session removed for user: {email}")
            return True
        return False
    
    def remove_user_sessions(self, email: str) -> int:
        """
        Remove all sessions for a specific user
        
        Args:
            email: User's email address
            
        Returns:
            int: Number of sessions removed
        """
        tokens_to_remove = []
        for token, data in self.active_sessions.items():
            if data["email"] == email:
                tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            del self.active_sessions[token]
        
        logger.info(f"Removed {len(tokens_to_remove)} sessions for user: {email}")
        return len(tokens_to_remove)
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions
        
        Returns:
            int: Number of sessions removed
        """
        now = datetime.now()
        expired_tokens = []
        
        for token, data in self.active_sessions.items():
            if now > data["expires_at"]:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.active_sessions[token]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
        
        return len(expired_tokens)
    
    def get_active_sessions_count(self) -> int:
        """Get the number of active sessions"""
        self.cleanup_expired_sessions()  # Clean up first
        return len(self.active_sessions)
    
    def get_user_sessions(self, email: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user
        
        Args:
            email: User's email address
            
        Returns:
            List[Dict]: List of session information
        """
        user_sessions = []
        for token, data in self.active_sessions.items():
            if data["email"] == email:
                session_info = {
                    "token": token,
                    "created_at": data["created_at"],
                    "expires_at": data["expires_at"],
                    "last_activity": data["last_activity"],
                    "domain": data["domain"]
                }
                user_sessions.append(session_info)
        
        return user_sessions

# Global session manager instance
session_manager = SessionManager()
