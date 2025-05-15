import os
import logging
import tempfile
from typing import Dict, Any, Optional, Tuple
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class TTSService:
    """Service for handling text-to-speech synthesis using ElevenLabs API"""
    
    # Map of language codes to recommended voice IDs
    LANGUAGE_VOICE_MAP = {
        "en": "EXAVITQu4vr4xnSDxMaL",  # Rachel - English (clear & neutral)
        "en-pidgin": "TxGEqnHWrfWFTfGW9XjX",  # Josh - Multilingual voice with good adaptability for Pidgin
        "yo": "jsCqWAovK2LkecY7zXl4",  # African - Yoruba approximation
        "ig": "jsCqWAovK2LkecY7zXl4",  # African - Igbo approximation
        "ha": "jsCqWAovK2LkecY7zXl4",  # African - Hausa approximation
        "fr": "t0jbNlBVZ17f02VDIeMI",  # Rémi - French
        "es": "ErXwobaYiN019PkySvjV",  # Antoni - Spanish
    }
    
    # Map of language codes to models
    LANGUAGE_MODEL_MAP = {
        "en": "eleven_turbo_v2",
        "en-pidgin": "eleven_turbo_v2",
        "yo": "eleven_multilingual_v2",
        "ig": "eleven_multilingual_v2",
        "ha": "eleven_multilingual_v2",
        "fr": "eleven_multilingual_v2",
        "es": "eleven_multilingual_v2",
    }
    
    # Map of voice IDs to custom voice settings
    VOICE_SETTINGS_MAP = {
        "CJsvtXkl6ObQJrCz44le": {  # Tapfuma Makina voice
            "stability": 0.58,     # 58% stability as requested
            "similarity_boost": 0.52,  # 52% similarity as requested 
            "style": 0.35,         # Default style
            "use_speaker_boost": True,  # Enhanced clarity
            "speed": 0.97          # 97% speed as requested
        },
        # Default settings for other voices
        "default": {
            "stability": 0.5,      # More natural, less robotic
            "similarity_boost": 0.75,  # Close to the original voice but with some flexibility
            "style": 0.35,         # Add some emotion/style to the voice
            "use_speaker_boost": True  # Enhanced clarity
        }
    }
    
    def __init__(self, raise_on_missing_env=False):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.initialized = False
        
        if not self.api_key:
            error_msg = "ElevenLabs API key not found in environment variables"
            logger.warning(error_msg)
            if raise_on_missing_env:
                raise ValueError(error_msg)
        else:
            # Initialize ElevenLabs client
            self.client = ElevenLabs(api_key=self.api_key)
            self.initialized = True
            logger.info("Initialized TTS service with ElevenLabs")
            
            # Cache available voices
            self.available_voices = {}
            self._cache_available_voices()
    
    def _cache_available_voices(self):
        """Cache available voices from ElevenLabs"""
        try:
            response = self.client.voices.get_all()
            for voice in response.voices:
                self.available_voices[voice.voice_id] = voice
            logger.info(f"Cached {len(self.available_voices)} voices from ElevenLabs")
        except Exception as e:
            logger.error(f"Error caching voices: {str(e)}")
    
    def get_voice_for_language(self, language_code: str) -> str:
        """
        Get an appropriate voice ID for the given language code
        
        Args:
            language_code: ISO language code (e.g., 'en', 'yo', 'ng')
            
        Returns:
            voice_id: Voice ID to use
        """
        self._check_initialized()
        
        voice_id = self.LANGUAGE_VOICE_MAP.get(language_code, self.LANGUAGE_VOICE_MAP["en"])
        
        # If specified voice not in available voices, use any available voice
        if voice_id not in self.available_voices and self.available_voices:
            voice_id = next(iter(self.available_voices.keys()))
        
        return voice_id
    
    def generate_speech(self, text: str, language_code: str = "en", voice_id: Optional[str] = None) -> bytes:
        """
        Generate speech from text
        
        Args:
            text: Text to convert to speech
            language_code: Language code for voice selection
            voice_id: Optional override for voice ID
            
        Returns:
            Audio data as bytes
        """
        self._check_initialized()
        
        try:
            # Get appropriate voice ID if not specified
            if not voice_id:
                voice_id = self.get_voice_for_language(language_code)
            
            # Get appropriate model for the language
            model_id = self.LANGUAGE_MODEL_MAP.get(language_code, "eleven_turbo_v2")
            
            # Log which voice and model we're using
            logger.info(f"Using voice ID: {voice_id} and model: {model_id} for language: {language_code}")
            
            # Configure voice settings for better quality
            voice_settings = self.VOICE_SETTINGS_MAP.get(voice_id, self.VOICE_SETTINGS_MAP["default"])
            
            # Generate audio
            audio_stream = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                voice_settings=voice_settings
            )
            
            # If the result is a generator (stream), convert it to bytes
            if hasattr(audio_stream, '__iter__') and not isinstance(audio_stream, bytes):
                audio_data = b''
                for chunk in audio_stream:
                    audio_data += chunk
            else:
                audio_data = audio_stream
            
            logger.info(f"Generated speech for text of length {len(text)}")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise
    
    def save_speech_to_file(self, text: str, output_path: str, language_code: str = "en", 
                           voice_id: Optional[str] = None) -> str:
        """
        Generate speech and save to file
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            language_code: Language code for voice selection
            voice_id: Optional override for voice ID
            
        Returns:
            Path to the saved audio file
        """
        self._check_initialized()
        
        try:
            # Generate speech (get bytes)
            audio_data = self.generate_speech(text, language_code, voice_id)
            
            # Save to file
            with open(output_path, "wb") as f:
                f.write(audio_data)
                
            logger.info(f"Saved speech to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving speech to file: {str(e)}")
            raise
    
    def generate_temp_speech_file(self, text: str, language_code: str = "en", 
                                 voice_id: Optional[str] = None) -> str:
        """
        Generate speech and save to a temporary file
        
        Args:
            text: Text to convert to speech
            language_code: Language code for voice selection
            voice_id: Optional override for voice ID
            
        Returns:
            Path to the temporary audio file
        """
        self._check_initialized()
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_file.close()
        
        # Generate speech and save to the temporary file
        self.save_speech_to_file(text, temp_file.name, language_code, voice_id)
        
        return temp_file.name
    
    def _check_initialized(self):
        """Check if the service is properly initialized"""
        if not self.initialized:
            raise ValueError("TTS service is not properly initialized. Check your environment variables.") 