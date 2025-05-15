import os
import logging
import random
import string
import time
from typing import Dict, Optional, List, Any
import jwt
from livekit import api
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LiveKitService:
    """Service for handling LiveKit room creation, tokens, and interactions"""
    
    def __init__(self, raise_on_missing_env=False):
        self.api_key = os.getenv('LIVEKIT_API_KEY')
        self.api_secret = os.getenv('LIVEKIT_API_SECRET')
        self.livekit_url = os.getenv('LIVEKIT_URL')
        self.initialized = False
        
        if not self.api_key or not self.api_secret or not self.livekit_url:
            error_msg = "LiveKit API key, secret or URL not found in environment variables"
            logger.warning(error_msg)
            if raise_on_missing_env:
                raise ValueError(error_msg)
        else:
            self.initialized = True
            logger.info(f"Initialized LiveKit service with URL: {self.livekit_url}")
        
    def generate_room_name(self, prefix="healthcare-") -> str:
        """Generate a unique room name with the given prefix"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}{random_suffix}"
    
    def create_token(self, room_name: str, user_identity: str, can_publish: bool = True, 
                    can_subscribe: bool = True) -> str:
        """
        Create a LiveKit access token for a specific room and user
        
        Args:
            room_name: Name of the LiveKit room
            user_identity: User identifier 
            can_publish: Whether the user can publish audio/video
            can_subscribe: Whether the user can subscribe to others
            
        Returns:
            JWT token string
        """
        self._check_initialized()
        
        try:
            # Get current time for JWT claims
            current_time = int(time.time())
            
            # Create a VideoGrant
            grant = {
                "video": {
                    "room": room_name,
                    "roomJoin": True,
                    "canPublish": can_publish,
                    "canSubscribe": can_subscribe
                }
            }
            
            # Set up the claims for the JWT token
            claims = {
                "iss": self.api_key,  # issuer - API key
                "sub": user_identity,  # subject - user identity
                "nbf": current_time,  # not before - current time
                "exp": current_time + 86400,  # expiration - 24 hours
                "name": user_identity,  # name of the participant
            }
            
            # Add the grant to the claims
            claims.update(grant)
            
            # Sign the token with API secret
            jwt_token = jwt.encode(
                claims,
                self.api_secret,
                algorithm="HS256"
            )
            
            logger.info(f"Generated token for user {user_identity} in room {room_name}")
            return jwt_token
            
        except Exception as e:
            logger.error(f"Error generating LiveKit token: {str(e)}")
            raise
    
    def create_or_join_room(self, conversation_id: str, user_identity: str) -> Dict[str, Any]:
        """
        Create or join a LiveKit room for a conversation
        
        Args:
            conversation_id: ID of the conversation
            user_identity: User identifier
            
        Returns:
            Dict with room details and access token
        """
        self._check_initialized()
        
        # Use conversation ID in room name for consistency
        room_name = f"healthcare-{conversation_id}"
        
        # Generate participant token
        token = self.create_token(room_name, user_identity)
        
        return {
            "room_name": room_name,
            "token": token,
            "livekit_url": self.livekit_url,
            "user_identity": user_identity
        }
    
    def _check_initialized(self):
        """Check if the service is properly initialized"""
        if not self.initialized:
            raise ValueError("LiveKit service is not properly initialized. Check your environment variables.")
    
    # Add more LiveKit service methods as needed 