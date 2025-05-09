from rest_framework import serializers
from .models import Task, ConversationSession, Message

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'completed', 'created_at', 'updated_at']

class ConversationSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationSession
        fields = ['id', 'created_at', 'updated_at']

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'session', 'role', 'content', 'timestamp'] 