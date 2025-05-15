from rest_framework import serializers
from .models import VoiceSession, VoiceTranscript, VoiceSessionParticipant

class VoiceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceSession
        fields = ['id', 'conversation', 'livekit_room_id', 'livekit_room_name', 'created_at', 'updated_at', 'active']
        read_only_fields = ['id', 'created_at', 'updated_at']

class VoiceSessionParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceSessionParticipant
        fields = ['id', 'session', 'identity', 'name', 'joined_at', 'last_active', 'is_active']
        read_only_fields = ['id', 'joined_at', 'last_active']

class VoiceTranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceTranscript
        fields = ['id', 'session', 'participant', 'transcript', 'confidence', 'is_final', 'timestamp', 'language_code']
        read_only_fields = ['id', 'timestamp'] 