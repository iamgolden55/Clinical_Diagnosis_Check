from django.shortcuts import render
import os
import json
import logging
import tempfile
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from api.models import ConversationSession

from .models import VoiceSession, VoiceTranscript, VoiceSessionParticipant
from .serializers import VoiceSessionSerializer, VoiceTranscriptSerializer, VoiceSessionParticipantSerializer
from .livekit_service import LiveKitService
from .asr_service import ASRService
from .tts_service import TTSService

# Setup logging
logger = logging.getLogger(__name__)

# Service instances will be initialized when needed
livekit_service = None
asr_service = None
tts_service = None

def get_livekit_service():
    """Get or initialize LiveKit service"""
    global livekit_service
    if livekit_service is None:
        livekit_service = LiveKitService(raise_on_missing_env=True)
    return livekit_service

def get_asr_service():
    """Get or initialize ASR service"""
    global asr_service
    if asr_service is None:
        asr_service = ASRService()
    return asr_service

def get_tts_service():
    """Get or initialize TTS service"""
    global tts_service
    if tts_service is None:
        tts_service = TTSService()
    return tts_service

class LiveKitTokenView(APIView):
    """View for generating LiveKit room tokens"""
    permission_classes = [AllowAny]  # For development, restrict in production
    
    def post(self, request):
        """Generate a LiveKit token for a room"""
        conversation_id = request.data.get('conversation_id')
        user_identity = request.data.get('user_identity', 'user')
        user_name = request.data.get('user_name', user_identity)
        
        if not conversation_id:
            return Response({'error': 'conversation_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get LiveKit service
            livekit_service = get_livekit_service()
            
            # Handle the conversation session retrieval
            conversation = None
            
            # If the conversation_id is a string with 'session-' prefix
            if isinstance(conversation_id, str) and conversation_id.startswith('session-'):
                # Get the first conversation session or create a new one
                existing_sessions = ConversationSession.objects.all()
                if existing_sessions.exists():
                    # Just use the first available session
                    conversation = existing_sessions.first()
                    logger.info(f"Using existing conversation session with ID {conversation.id}")
                else:
                    # Create a new session if none exist
                    conversation = ConversationSession.objects.create()
                    logger.info(f"Created new conversation session with ID {conversation.id}")
            else:
                # Try to use the ID directly
                try:
                    conversation_id_int = int(conversation_id)
                    # Try to get by exact ID
                    try:
                        conversation = ConversationSession.objects.get(id=conversation_id_int)
                        logger.info(f"Found conversation session with ID {conversation.id}")
                    except ConversationSession.DoesNotExist:
                        # Create with specific ID
                        conversation = ConversationSession.objects.create(id=conversation_id_int)
                        logger.info(f"Created new conversation session with ID {conversation.id}")
                    except ConversationSession.MultipleObjectsReturned:
                        # In case of multiple objects, take the first one
                        conversation = ConversationSession.objects.filter(id=conversation_id_int).first()
                        logger.info(f"Found multiple session with ID {conversation_id_int}, using first one with ID {conversation.id}")
                except (ValueError, TypeError):
                    # If conversion fails, use the first session or create one
                    conversation = ConversationSession.objects.first() or ConversationSession.objects.create()
                    logger.info(f"Using/creating conversation session with ID {conversation.id}")
            
            # Get room details and token from LiveKit service
            room_details = livekit_service.create_or_join_room(str(conversation.id), user_identity)
            
            # Get or create a voice session for this conversation
            try:
                voice_session = VoiceSession.objects.get(
                    conversation=conversation,
                    livekit_room_name=room_details['room_name']
                )
                logger.info(f"Found existing voice session for conversation {conversation.id}")
            except VoiceSession.DoesNotExist:
                voice_session = VoiceSession.objects.create(
                    conversation=conversation,
                    livekit_room_name=room_details['room_name'],
                    livekit_room_id=room_details['room_name'],
                    active=True
                )
                logger.info(f"Created new voice session for conversation {conversation.id}")
            except VoiceSession.MultipleObjectsReturned:
                voice_session = VoiceSession.objects.filter(
                    conversation=conversation,
                    livekit_room_name=room_details['room_name']
                ).first()
                logger.info(f"Found multiple voice sessions, using first one")
            
            # Create or update participant
            try:
                participant = VoiceSessionParticipant.objects.get(
                    session=voice_session,
                    identity=user_identity
                )
                # Update participant
                participant.name = user_name
                participant.is_active = True
                participant.save()
                logger.info(f"Updated participant {user_identity}")
            except VoiceSessionParticipant.DoesNotExist:
                participant = VoiceSessionParticipant.objects.create(
                    session=voice_session,
                    identity=user_identity,
                    name=user_name,
                    is_active=True
                )
                logger.info(f"Created new participant {user_identity}")
            except VoiceSessionParticipant.MultipleObjectsReturned:
                participant = VoiceSessionParticipant.objects.filter(
                    session=voice_session,
                    identity=user_identity
                ).first()
                participant.name = user_name
                participant.is_active = True
                participant.save()
                logger.info(f"Found multiple participants, updated first one")
            
            return Response({
                'token': room_details['token'],
                'room_name': room_details['room_name'],
                'livekit_url': room_details['livekit_url'],
                'voice_session_id': voice_session.id,
                'participant_id': participant.id
            })
            
        except Exception as e:
            logger.error(f"Error generating LiveKit token: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TranscribeAudioView(APIView):
    """View for transcribing audio to text using ASR"""
    permission_classes = [AllowAny]  # For development, restrict in production
    
    def post(self, request):
        """Transcribe an audio file/data"""
        voice_session_id = request.data.get('voice_session_id')
        participant_id = request.data.get('participant_id')
        language = request.data.get('language')
        audio_file = request.FILES.get('audio')
        
        if not voice_session_id:
            return Response({'error': 'voice_session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not audio_file:
            return Response({'error': 'audio file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get ASR service
            asr_service = get_asr_service()
            
            # Get the voice session
            voice_session = get_object_or_404(VoiceSession, id=voice_session_id)
            
            # Get the participant if provided
            participant = None
            if participant_id:
                participant = get_object_or_404(VoiceSessionParticipant, id=participant_id, session=voice_session)
            
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                for chunk in audio_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            # Transcribe the audio
            transcription_result = asr_service.transcribe_audio_file(temp_file_path, language)
            
            # Save transcription to database
            transcript = VoiceTranscript.objects.create(
                session=voice_session,
                participant=participant,
                transcript=transcription_result['text'],
                confidence=transcription_result.get('confidence', 0.0),
                is_final=True,
                language_code=transcription_result.get('language', language or 'en')
            )
            
            # Delete temporary file
            os.unlink(temp_file_path)
            
            # Extract language for response if not provided
            detected_language = transcription_result.get('language', language or 'en')
            
            return Response({
                'transcript': transcription_result['text'],
                'confidence': transcription_result.get('confidence', 0.0),
                'language': detected_language,
                'transcript_id': transcript.id
            })
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TextToSpeechView(APIView):
    """View for converting text to speech using TTS"""
    permission_classes = [AllowAny]  # For development, restrict in production
    
    def post(self, request):
        """Convert text to speech"""
        voice_session_id = request.data.get('voice_session_id')
        text = request.data.get('text')
        language_code = request.data.get('language_code', 'en')
        voice_id = request.data.get('voice_id')
        
        if not voice_session_id:
            return Response({'error': 'voice_session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not text:
            return Response({'error': 'text is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get TTS service
            tts_service = get_tts_service()
            
            # Get the voice session
            voice_session = get_object_or_404(VoiceSession, id=voice_session_id)
            
            # Clean up markdown formatting from text
            import re
            # Remove bold/italic markers
            text = re.sub(r'\*\*|\*|__|\^', '', text)
            # Remove other common markdown
            text = re.sub(r'\[|\]|\(|\)|#|`', '', text)
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            logger.info(f"Cleaned text for TTS: {text[:100]}...")
            
            # Special formatting for Nigerian Pidgin responses
            if language_code == 'en-pidgin':
                logger.info("Applying Nigerian Pidgin speech formatting")
                # No need to modify the text, just log for clarity
            
            # Generate speech
            logger.info(f"Generating speech for language code: {language_code}")
            audio_data = tts_service.generate_speech(text, language_code, voice_id)
            
            # Return binary audio data using HttpResponse to prevent UTF-8 decoding attempts
            from django.http import HttpResponse
            response = HttpResponse(audio_data, content_type='audio/mpeg')
            response['Content-Disposition'] = 'attachment; filename="speech.mp3"'
            return response
            
        except Exception as e:
            logger.error(f"Error converting text to speech: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VoiceSessionView(APIView):
    """View for managing voice sessions"""
    permission_classes = [AllowAny]  # For development, restrict in production
    
    def get(self, request, session_id=None):
        """Get voice session details"""
        if session_id:
            # Get a specific voice session
            voice_session = get_object_or_404(VoiceSession, id=session_id)
            serializer = VoiceSessionSerializer(voice_session)
            return Response(serializer.data)
        else:
            # List all active voice sessions
            voice_sessions = VoiceSession.objects.filter(active=True)
            serializer = VoiceSessionSerializer(voice_sessions, many=True)
            return Response(serializer.data)
    
    def post(self, request):
        """Create a new voice session"""
        serializer = VoiceSessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, session_id):
        """Update a voice session"""
        voice_session = get_object_or_404(VoiceSession, id=session_id)
        serializer = VoiceSessionSerializer(voice_session, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, session_id):
        """Delete (deactivate) a voice session"""
        voice_session = get_object_or_404(VoiceSession, id=session_id)
        voice_session.active = False
        voice_session.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantView(APIView):
    """View for managing voice session participants"""
    permission_classes = [AllowAny]  # For development, restrict in production
    
    def get(self, request, session_id, participant_id=None):
        """Get participant details"""
        voice_session = get_object_or_404(VoiceSession, id=session_id)
        
        if participant_id:
            # Get a specific participant
            participant = get_object_or_404(VoiceSessionParticipant, id=participant_id, session=voice_session)
            serializer = VoiceSessionParticipantSerializer(participant)
            return Response(serializer.data)
        else:
            # List all participants in the session
            participants = VoiceSessionParticipant.objects.filter(session=voice_session)
            serializer = VoiceSessionParticipantSerializer(participants, many=True)
            return Response(serializer.data)
    
    def post(self, request, session_id):
        """Add a participant to a session"""
        voice_session = get_object_or_404(VoiceSession, id=session_id)
        
        # Add session to request data
        data = request.data.copy()
        data['session'] = voice_session.id
        
        serializer = VoiceSessionParticipantSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, session_id, participant_id):
        """Update a participant"""
        voice_session = get_object_or_404(VoiceSession, id=session_id)
        participant = get_object_or_404(VoiceSessionParticipant, id=participant_id, session=voice_session)
        
        serializer = VoiceSessionParticipantSerializer(participant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, session_id, participant_id):
        """Mark a participant as inactive"""
        voice_session = get_object_or_404(VoiceSession, id=session_id)
        participant = get_object_or_404(VoiceSessionParticipant, id=participant_id, session=voice_session)
        
        participant.is_active = False
        participant.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
