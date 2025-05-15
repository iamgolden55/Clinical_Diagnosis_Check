from django.urls import path
from .views import (
    LiveKitTokenView,
    TranscribeAudioView,
    TextToSpeechView,
    VoiceSessionView,
    ParticipantView
)

urlpatterns = [
    # LiveKit token generation
    path('token/', LiveKitTokenView.as_view(), name='livekit-token'),
    
    # Voice session management
    path('sessions/', VoiceSessionView.as_view(), name='voice-sessions'),
    path('sessions/<int:session_id>/', VoiceSessionView.as_view(), name='voice-session-detail'),
    
    # Participant management
    path('sessions/<int:session_id>/participants/', ParticipantView.as_view(), name='voice-session-participants'),
    path('sessions/<int:session_id>/participants/<int:participant_id>/', ParticipantView.as_view(), name='voice-session-participant-detail'),
    
    # Speech-to-Text (ASR)
    path('transcribe/', TranscribeAudioView.as_view(), name='transcribe-audio'),
    
    # Text-to-Speech (TTS)
    path('synthesize/', TextToSpeechView.as_view(), name='text-to-speech'),
] 