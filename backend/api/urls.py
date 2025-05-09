from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, ChatAPIView, ChatSummaryAPIView

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='chat'),
    path('chat/summary/', ChatSummaryAPIView.as_view(), name='chat_summary'),
    path('', include(router.urls)),
] 