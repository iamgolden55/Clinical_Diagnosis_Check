from django.db import models
from api.models import ConversationSession

class VoiceSession(models.Model):
    """Model to track voice conversation sessions"""
    conversation = models.ForeignKey(
        ConversationSession, 
        on_delete=models.CASCADE,
        related_name='voice_sessions'
    )
    livekit_room_id = models.CharField(max_length=255)
    livekit_room_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Voice Session for {self.conversation.id} ({self.livekit_room_name})"

class VoiceSessionParticipant(models.Model):
    """Model to track participants in a voice session"""
    session = models.ForeignKey(
        VoiceSession,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    identity = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True, null=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Participant {self.identity} in {self.session.livekit_room_name}"

class VoiceTranscript(models.Model):
    """Model to store voice transcripts from speech recognition"""
    session = models.ForeignKey(
        VoiceSession,
        on_delete=models.CASCADE,
        related_name='transcripts'
    )
    participant = models.ForeignKey(
        VoiceSessionParticipant,
        on_delete=models.SET_NULL,
        related_name='transcripts',
        null=True,
        blank=True
    )
    transcript = models.TextField()
    confidence = models.FloatField(default=0.0)
    is_final = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    language_code = models.CharField(max_length=10, default='en')
    
    def __str__(self):
        return f"Transcript at {self.timestamp} (Final: {self.is_final})"
