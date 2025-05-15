from django.db import models

# Create your models here.

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ConversationSession(models.Model):
    """
    Represents a chat session between a user and the AI assistant.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class Message(models.Model):
    """
    Stores individual messages in a ConversationSession.
    """
    ROLE_CHOICES = [
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    ]
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        snippet = self.content[:20].replace("\n", " ")
        return f"[{self.session.id}] {self.role}: {snippet}"

class Feedback(models.Model):
    """Model to store user feedback on AI responses"""
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    user_query = models.TextField(blank=True)
    response_text = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField()  # Rating from 1-5
    culturally_appropriate = models.BooleanField(default=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback: {self.rating}/5 - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class UserContext(models.Model):
    """
    Stores medical context for a conversation session to maintain information throughout interactions
    """
    session = models.OneToOneField(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name='medical_context'
    )
    symptoms = models.JSONField(default=dict, blank=True)
    symptom_durations = models.JSONField(default=dict, blank=True)
    treatments_tried = models.JSONField(default=list, blank=True)
    medical_history = models.JSONField(default=list, blank=True)
    cultural_preferences = models.JSONField(default=dict, blank=True)
    language = models.CharField(max_length=20, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Medical Context for Session {self.session.id}"

class ExpertReview(models.Model):
    """
    Stores expert reviews for AI responses
    """
    feedback = models.ForeignKey(
        Feedback,
        on_delete=models.CASCADE,
        related_name='expert_reviews'
    )
    reviewer_name = models.CharField(max_length=100)
    medical_accuracy = models.PositiveSmallIntegerField()  # 1-5 rating
    cultural_relevance = models.PositiveSmallIntegerField()  # 1-5 rating
    suggested_correction = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Expert Review by {self.reviewer_name} - {self.created_at.strftime('%Y-%m-%d')}"

class AnalyticsMetric(models.Model):
    """
    Stores aggregated analytics metrics for dashboard visualization
    """
    METRIC_TYPES = [
        ('avg_rating', 'Average Rating'),
        ('cultural_score', 'Cultural Appropriateness Score'),
        ('response_time', 'Average Response Time'),
        ('feedback_count', 'Feedback Count'),
        ('common_issue', 'Common Issue'),
    ]
    
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    value = models.FloatField()
    text_value = models.TextField(blank=True, null=True)  # For storing text-based metrics
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value} ({self.date})"
