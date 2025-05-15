import os
import logging
import tempfile
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ASRService:
    """Service for handling speech-to-text transcription using OpenAI Whisper API"""
    
    def __init__(self, raise_on_missing_env=False):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.initialized = False
        
        if not self.api_key:
            error_msg = "OpenAI API key not found in environment variables"
            logger.warning(error_msg)
            if raise_on_missing_env:
                raise ValueError(error_msg)
        else:
            self.client = OpenAI(api_key=self.api_key)
            self.initialized = True
            logger.info("Initialized ASR service with OpenAI Whisper")
    
    def transcribe_audio_file(self, audio_file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI Whisper API
        
        Args:
            audio_file_path: Path to audio file
            language: Optional language code (e.g., 'en', 'yo', 'en-pidgin')
            
        Returns:
            Dict with transcription result
        """
        self._check_initialized()
        
        try:
            # Prepare options for transcription
            options = {}
            
            # Map special language codes to supported Whisper languages
            language_map = {
                'en-pidgin': 'en',  # Nigerian Pidgin - use English model but we'll handle it specially
            }
            
            # Store original language for reference
            original_language = language
            
            # Special handling for certain languages
            if language == 'en-pidgin':
                # Add a comprehensive prompt to help Whisper understand Nigerian Pidgin
                options["prompt"] = """
                This is Nigerian Pidgin English. Common phrases and patterns include:
                'How you dey' (How are you)
                'Abeg' (Please)
                'Wahala' (Trouble)
                'I wan chop' (I want to eat)
                'Belle' (Stomach)
                'Na so' (That's how it is)
                'Afar' (Far)
                'Dey pain me' (It hurts)
                'My belle dey pain me' (My stomach hurts)
                'How far' (What's up)
                'I no know' (I don't know)
                'Wetin' (What)
                'Oga' (Boss/Sir)
                'No wahala' (No problem)
                'Chop' (Eat)
                'I dey' (I am)
                'Make I' (Let me)
                """
            
            # Map language code if needed
            if language in language_map:
                language = language_map[language]
                logger.info(f"Mapped language code from {original_language} to {language}")
            
            if language:
                options["language"] = language
            
            # Open audio file and transcribe
            with open(audio_file_path, "rb") as audio_file:
                logger.info(f"Sending transcription request with language: {language}, options: {options}")
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",  # Standard model with guaranteed availability
                    file=audio_file,
                    **options
                )
                
            # Log the transcription result
            logger.info(f"Transcription result: {response.text}")
            
            # Create response object
            result = {
                "text": response.text,
                "confidence": 0.9,  # Whisper API doesn't return confidence, using default
                "original_language": original_language  # Store the original requested language
            }
            
            # Add language if provided
            if language:
                result["language"] = language
            
            logger.info(f"Transcribed audio file: {audio_file_path} with language: {language}")
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio file: {str(e)}")
            raise
    
    def transcribe_audio_bytes(self, audio_bytes: bytes, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio from bytes using OpenAI Whisper API
        
        Args:
            audio_bytes: Audio data as bytes
            language: Optional language code (e.g., 'en', 'yo', 'en-pidgin')
            
        Returns:
            Dict with transcription result
        """
        self._check_initialized()
        
        try:
            # Save bytes to temporary file
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            # Transcribe the temporary file
            result = self.transcribe_audio_file(temp_file_path, language)
            
            # Delete the temporary file
            os.unlink(temp_file_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio bytes: {str(e)}")
            raise
    
    def _check_initialized(self):
        """Check if the service is properly initialized"""
        if not self.initialized:
            raise ValueError("ASR service is not properly initialized. Check your environment variables.") 