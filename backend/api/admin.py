from django.contrib import admin
from .models import Task, ConversationSession, Message, Feedback

# Register your models here.
admin.site.register(Task)
admin.site.register(ConversationSession)
admin.site.register(Message)
admin.site.register(Feedback)
