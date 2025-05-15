from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskViewSet, ChatAPIView, ChatSummaryAPIView, FeedbackAPIView,
    UserContextAPIView, ExpertReviewAPIView, AnalyticsAPIView, AnalyticsDashboardAPIView,
    DataPipelineView
)

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', ChatAPIView.as_view(), name='chat'),
    path('chat/summary/', ChatSummaryAPIView.as_view(), name='chat-summary'),
    path('feedback/', FeedbackAPIView.as_view(), name='feedback'),
    path('user-context/', UserContextAPIView.as_view(), name='user-context'),
    path('expert-review/', ExpertReviewAPIView.as_view(), name='expert-review'),
    path('analytics/', AnalyticsAPIView.as_view(), name='analytics'),
    path('analytics/dashboard/', AnalyticsDashboardAPIView.as_view(), name='analytics-dashboard'),
    path('data-pipeline/', DataPipelineView.as_view(), name='data-pipeline'),
] 