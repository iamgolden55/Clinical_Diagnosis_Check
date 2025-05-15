"""
Data Pipeline for Model Training

This module processes feedback data and prepares it for model training.
It includes functions to:
1. Extract valuable insights from user feedback
2. Process and structure data for model fine-tuning
3. Generate analytics metrics for dashboard visualization
"""

import os
import json
import datetime
from django.db.models import Avg, Count, Q, FloatField, Case, When, F, ExpressionWrapper
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
import pandas as pd
import numpy as np
from collections import Counter

from .models import Feedback, ExpertReview, UserContext, AnalyticsMetric, ConversationSession, Message

class DataPipeline:
    """
    Pipeline for processing feedback data and preparing it for model training
    """
    
    def __init__(self):
        """Initialize the data pipeline"""
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
    def extract_metrics(self, from_date=None, to_date=None):
        """
        Extract and compute metrics from feedback data
        
        Args:
            from_date (datetime): Start date for data extraction
            to_date (datetime): End date for data extraction
            
        Returns:
            dict: Dictionary containing extracted metrics
        """
        if not from_date:
            from_date = timezone.now().date() - datetime.timedelta(days=30)
        if not to_date:
            to_date = timezone.now().date()
            
        metrics = {
            'total_feedback': 0,
            'avg_rating': 0,
            'cultural_score': 0,
            'common_issues': [],
            'time_series': {},
            'by_language': {},
        }
        
        # Get feedback data in date range
        feedback_data = Feedback.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        )
        
        if not feedback_data.exists():
            return metrics
            
        # Calculate basic metrics
        metrics['total_feedback'] = feedback_data.count()
        avg_rating = feedback_data.aggregate(avg=Avg('rating'))
        metrics['avg_rating'] = avg_rating['avg'] or 0
        
        # Cultural appropriateness score
        cultural_count = feedback_data.filter(culturally_appropriate=True).count()
        if metrics['total_feedback'] > 0:
            metrics['cultural_score'] = (cultural_count / metrics['total_feedback']) * 100
            
        # Extract common issues from comments using simple keyword extraction
        comments = feedback_data.exclude(comment='').values_list('comment', flat=True)
        common_issues = self._extract_common_issues(comments)
        metrics['common_issues'] = common_issues[:5]  # Top 5 issues
        
        # Generate time series data
        metrics['time_series'] = self._generate_time_series(feedback_data)
        
        # Group by language if UserContext is available
        user_contexts = UserContext.objects.filter(session__in=feedback_data.values_list('session', flat=True))
        if user_contexts.exists():
            metrics['by_language'] = self._group_by_language(feedback_data, user_contexts)
            
        return metrics
        
    def _extract_common_issues(self, comments):
        """
        Extract common issues mentioned in feedback comments
        
        Args:
            comments (list): List of feedback comments
            
        Returns:
            list: List of common issue tuples (issue, count)
        """
        # Keywords for different issue categories
        issue_keywords = {
            'cultural_relevance': ['cultural', 'tradition', 'local', 'belief', 'inappropriate'],
            'medical_accuracy': ['wrong', 'incorrect', 'accurate', 'inaccurate', 'misleading'],
            'clarity': ['unclear', 'confusing', 'vague', 'complex', 'difficult'],
            'completeness': ['incomplete', 'missing', 'lacking', 'partial', 'more information'],
            'relevance': ['irrelevant', 'not relevant', 'unrelated', 'off-topic'],
            'technical_issue': ['error', 'bug', 'crash', 'failed', 'technical', 'not working'],
            'language': ['language', 'translation', 'pidgin', 'dialect', 'accent'],
        }
        
        issue_counts = Counter()
        
        for comment in comments:
            comment_lower = comment.lower()
            for issue, keywords in issue_keywords.items():
                if any(keyword in comment_lower for keyword in keywords):
                    issue_counts[issue] += 1
                    
        # Convert to list of tuples (issue, count) and sort by count
        return [(issue, count) for issue, count in issue_counts.most_common()]
        
    def _generate_time_series(self, feedback_data):
        """
        Generate time series data from feedback
        
        Args:
            feedback_data (QuerySet): Feedback data queryset
            
        Returns:
            dict: Dictionary with time series data
        """
        time_series = {
            'daily': {},
            'weekly': {},
            'monthly': {},
        }
        
        # Daily metrics
        daily_metrics = feedback_data.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            avg_rating=Avg('rating'),
            count=Count('id'),
            cultural_appropriate_count=Count('id', filter=Q(culturally_appropriate=True))
        ).order_by('date')
        
        for metric in daily_metrics:
            date_str = metric['date'].isoformat()
            cultural_score = 0
            if metric['count'] > 0:
                cultural_score = (metric['cultural_appropriate_count'] / metric['count']) * 100
                
            time_series['daily'][date_str] = {
                'avg_rating': metric['avg_rating'],
                'count': metric['count'],
                'cultural_score': cultural_score,
            }
            
        # Weekly metrics
        weekly_metrics = feedback_data.annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            avg_rating=Avg('rating'),
            count=Count('id')
        ).order_by('week')
        
        for metric in weekly_metrics:
            week_str = metric['week'].isoformat()
            time_series['weekly'][week_str] = {
                'avg_rating': metric['avg_rating'],
                'count': metric['count'],
            }
            
        # Monthly metrics
        monthly_metrics = feedback_data.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            avg_rating=Avg('rating'),
            count=Count('id')
        ).order_by('month')
        
        for metric in monthly_metrics:
            month_str = metric['month'].isoformat()
            time_series['monthly'][month_str] = {
                'avg_rating': metric['avg_rating'],
                'count': metric['count'],
            }
            
        return time_series
        
    def _group_by_language(self, feedback_data, user_contexts):
        """
        Group metrics by language preference
        
        Args:
            feedback_data (QuerySet): Feedback data queryset
            user_contexts (QuerySet): UserContext queryset
            
        Returns:
            dict: Metrics grouped by language
        """
        by_language = {}
        
        # Create a mapping of session_id to language
        session_to_language = {
            context.session_id: context.language
            for context in user_contexts
        }
        
        # Group feedback by language
        for feedback in feedback_data:
            language = session_to_language.get(feedback.session_id, 'unknown')
            
            if language not in by_language:
                by_language[language] = {
                    'count': 0,
                    'ratings': [],
                    'cultural_appropriate': 0,
                }
                
            by_language[language]['count'] += 1
            by_language[language]['ratings'].append(feedback.rating)
            if feedback.culturally_appropriate:
                by_language[language]['cultural_appropriate'] += 1
        
        # Calculate averages
        for language, data in by_language.items():
            if data['count'] > 0:
                data['avg_rating'] = sum(data['ratings']) / data['count']
                data['cultural_score'] = (data['cultural_appropriate'] / data['count']) * 100
            else:
                data['avg_rating'] = 0
                data['cultural_score'] = 0
            
            # Remove raw data
            del data['ratings']
            
        return by_language
    
    def prepare_training_data(self, from_date=None, to_date=None, min_rating=None, export=True):
        """
        Prepare training data from feedback and conversations
        
        Args:
            from_date (datetime): Start date for data extraction
            to_date (datetime): End date for data extraction
            min_rating (int): Minimum rating threshold (1-5)
            export (bool): Whether to export the data to files
            
        Returns:
            dict: Dictionary with training data statistics
        """
        if not from_date:
            from_date = timezone.now().date() - datetime.timedelta(days=90)  # Default to last 90 days
        if not to_date:
            to_date = timezone.now().date()
            
        # Filter feedback based on criteria
        feedback_query = Feedback.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        )
        
        if min_rating is not None:
            feedback_query = feedback_query.filter(rating__gte=min_rating)
            
        # Collect training samples
        training_samples = []
        
        for feedback in feedback_query:
            # Get the conversation
            messages = Message.objects.filter(session=feedback.session).order_by('timestamp')
            
            if not messages.exists():
                continue
                
            # Extract the conversation history
            conversation = []
            
            for msg in messages:
                conversation.append({
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                })
                
            # Get user context if available
            context_data = {}
            try:
                user_context = UserContext.objects.get(session=feedback.session)
                context_data = {
                    'symptoms': user_context.symptoms,
                    'symptom_durations': user_context.symptom_durations,
                    'treatments_tried': user_context.treatments_tried,
                    'medical_history': user_context.medical_history,
                    'cultural_preferences': user_context.cultural_preferences,
                    'language': user_context.language,
                }
            except UserContext.DoesNotExist:
                pass
                
            # Get expert reviews if available
            expert_reviews = []
            for review in ExpertReview.objects.filter(feedback=feedback):
                expert_reviews.append({
                    'reviewer_name': review.reviewer_name,
                    'medical_accuracy': review.medical_accuracy,
                    'cultural_relevance': review.cultural_relevance,
                    'suggested_correction': review.suggested_correction,
                    'additional_notes': review.additional_notes,
                })
                
            # Create a training sample
            sample = {
                'feedback_id': feedback.id,
                'conversation': conversation,
                'user_context': context_data,
                'feedback': {
                    'rating': feedback.rating,
                    'culturally_appropriate': feedback.culturally_appropriate,
                    'comment': feedback.comment,
                },
                'expert_reviews': expert_reviews,
            }
            
            training_samples.append(sample)
            
        # Export to file if requested
        if export and training_samples:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f'training_data_{timestamp}.json'
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(training_samples, f, indent=2)
                
        # Return statistics
        return {
            'total_samples': len(training_samples),
            'with_expert_reviews': sum(1 for sample in training_samples if sample['expert_reviews']),
            'with_user_context': sum(1 for sample in training_samples if sample['user_context']),
            'by_rating': Counter(sample['feedback']['rating'] for sample in training_samples),
            'export_path': filepath if export and training_samples else None,
        }
    
    def update_analytics_metrics(self, from_date=None, to_date=None):
        """
        Update the AnalyticsMetric model with new metrics
        
        Args:
            from_date (datetime): Start date for data extraction
            to_date (datetime): End date for data extraction
            
        Returns:
            dict: Statistics about updated metrics
        """
        if not from_date:
            # Default to the last month if not specified
            latest_metric = AnalyticsMetric.objects.all().order_by('-date').first()
            if latest_metric:
                from_date = latest_metric.date + datetime.timedelta(days=1)
            else:
                from_date = timezone.now().date() - datetime.timedelta(days=30)
                
        if not to_date:
            to_date = timezone.now().date()
            
        # Extract metrics
        metrics = self.extract_metrics(from_date, to_date)
        
        # Update or create analytics metrics
        updated_count = 0
        created_count = 0
        
        # Process time series data
        if 'time_series' in metrics and 'daily' in metrics['time_series']:
            for date_str, daily_data in metrics['time_series']['daily'].items():
                date = datetime.date.fromisoformat(date_str)
                
                # Average rating
                metric, created = AnalyticsMetric.objects.update_or_create(
                    metric_type='avg_rating',
                    date=date,
                    defaults={'value': daily_data['avg_rating']}
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
                # Cultural score
                if 'cultural_score' in daily_data:
                    metric, created = AnalyticsMetric.objects.update_or_create(
                        metric_type='cultural_score',
                        date=date,
                        defaults={'value': daily_data['cultural_score']}
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                # Feedback count
                metric, created = AnalyticsMetric.objects.update_or_create(
                    metric_type='feedback_count',
                    date=date,
                    defaults={'value': daily_data['count']}
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
        # Common issues - store as a single metric with the latest date
        if metrics['common_issues']:
            # Convert to format for storage
            issues_text = '; '.join(f"{issue}: {count}" for issue, count in metrics['common_issues'])
            
            metric, created = AnalyticsMetric.objects.update_or_create(
                metric_type='common_issue',
                date=to_date,
                defaults={
                    'value': len(metrics['common_issues']),
                    'text_value': issues_text
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
                
        return {
            'metrics_created': created_count,
            'metrics_updated': updated_count,
            'date_range': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            }
        }


# Helper functions for direct use in views

def process_and_update_metrics(from_date=None, to_date=None):
    """
    Process feedback data and update analytics metrics
    
    Args:
        from_date (datetime): Start date for data extraction
        to_date (datetime): End date for data extraction
        
    Returns:
        dict: Result statistics
    """
    pipeline = DataPipeline()
    return pipeline.update_analytics_metrics(from_date, to_date)
    
def generate_training_data(from_date=None, to_date=None, min_rating=4):
    """
    Generate training data from feedback and conversations
    
    Args:
        from_date (datetime): Start date for data extraction
        to_date (datetime): End date for data extraction
        min_rating (int): Minimum rating threshold (1-5)
        
    Returns:
        dict: Result statistics
    """
    pipeline = DataPipeline()
    return pipeline.prepare_training_data(from_date, to_date, min_rating) 