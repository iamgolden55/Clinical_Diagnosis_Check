from rest_framework import serializers
from .models import Task, ConversationSession, Message, Feedback, UserContext, ExpertReview, AnalyticsMetric

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

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'session', 'user_query', 'response_text', 'rating', 
                 'culturally_appropriate', 'comment', 'created_at']

class UserContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserContext
        fields = ['id', 'session', 'symptoms', 'symptom_durations', 
                 'treatments_tried', 'medical_history', 'cultural_preferences', 
                 'language', 'created_at', 'updated_at']

class ExpertReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertReview
        fields = ['id', 'feedback', 'reviewer_name', 'medical_accuracy', 
                 'cultural_relevance', 'suggested_correction', 
                 'additional_notes', 'created_at']

class AnalyticsMetricSerializer(serializers.ModelSerializer):
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    
    class Meta:
        model = AnalyticsMetric
        fields = ['id', 'metric_type', 'metric_type_display', 'value', 
                 'text_value', 'date', 'created_at'] 