from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Task
from .serializers import (
    TaskSerializer, ConversationSessionSerializer, MessageSerializer, 
    FeedbackSerializer, UserContextSerializer, ExpertReviewSerializer, 
    AnalyticsMetricSerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
import os
from dotenv import load_dotenv
from openai import OpenAI
# Import LangChain components
from langchain_community.chat_models import ChatOpenAI
from langchain.chains.llm import LLMChain
from langchain.chains.conversation.base import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

from .models import ConversationSession, Message, UserContext, ExpertReview, AnalyticsMetric
from .medical_ner import extract_medical_entities, analyze_patient_emotion
import logging
from .data_pipeline import DataPipeline, process_and_update_metrics, generate_training_data

# Set up logging
logger = logging.getLogger(__name__)

def get_or_create_conversation_session(session_id):
    """Get or create a conversation session based on the provided ID"""
    # Handle string-based session IDs (e.g., 'session-xxxx')
    if isinstance(session_id, str) and session_id.startswith('session-'):
        # Find an existing session or create one
        existing_sessions = ConversationSession.objects.all()
        if existing_sessions.exists():
            return existing_sessions.first()
        else:
            return ConversationSession.objects.create()
    
    # Handle numeric session IDs
    try:
        session_id_int = int(session_id)
        try:
            return ConversationSession.objects.get(id=session_id_int)
        except ConversationSession.DoesNotExist:
            return ConversationSession.objects.create(id=session_id_int)
        except ConversationSession.MultipleObjectsReturned:
            return ConversationSession.objects.filter(id=session_id_int).first()
    except (ValueError, TypeError):
        # If conversion fails, use the first session or create one
        return ConversationSession.objects.first() or ConversationSession.objects.create()

def get_conversation_history(session):
    """Get conversation history for a session"""
    return session.messages.order_by('timestamp')

def save_message(session, role, content):
    """Save a message to the database"""
    return Message.objects.create(session=session, role=role, content=content)

def is_pure_pidgin(text):
    pidgin_keywords = [
        "bele", "wahala", "dey", "go", "no worry", "abeg", "small-small", "pain me", "comot",
        "gist", "how far", "na", "wetin", "palava", "waka", "chop", "fit", "no vex", "e don tey",
        "you sabi", "make i", "e go beta", "na true", "shey", "abi", "you no go", "carry go",
        "una", "you dey", "i dey", "weytin happen", "no be small", "as e be so", "aswear",
        "wahala dey", "e be like say", "oya", "dey alright", "i don try", "e reach", "sharp sharp",
        "no be me", "i no sabi", "you try", "you no try", "you no serious", "e shock me",
        "na wa", "e no easy", "as per", "just dey", "biko", "shapaly", "dey there", "my guy",
        "oga", "mad o", "e pain me", "no time", "na wetin", "jare", "ehn now", "no shaking"
    ]
    return any(word in text.lower() for word in pidgin_keywords)

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by('-created_at')
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]  # For development, restrict in production

class ChatAPIView(APIView):
    """Handle chat messages: save user message, get LangChain to generate a response using chat memory."""
    permission_classes = [AllowAny]
    model = "gpt-4o"
    
    def post(self, request):
        """Handle chat requests"""
        message = request.data.get('message', '')
        session_id = request.data.get('session_id', 'default')
        
        if not message:
            return Response({'error': 'No message provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get or create a ConversationSession
            session = get_or_create_conversation_session(session_id)
            
            # Get chat history
            messages = get_conversation_history(session)
            
            # Add system prompt for Nigerian Pidgin if detected
            pidgin_indicators = ["dey", "abeg", "belle", "na", "wetin", "wahala", "chop"]
            has_pidgin = any(indicator in message.lower() for indicator in pidgin_indicators)
            
            # Set up the system prompt based on content
            system_prompt = """You are EleraAI, a healthcare assistant specializing in providing medical information for users in African regions.

When responding to health concerns:
1. Provide accurate, clear and compassionate healthcare advice
2. Ask follow-up questions to better understand the user's condition (always include at least one relevant follow-up question)
3. Inquire about both modern and traditional remedies they might have tried
4. Be sensitive to cultural contexts around health and acknowledge local healing practices
5. Clearly state when a condition requires professional medical attention
6. Use a conversational, warm tone without excessive formatting

For symptom assessment, follow this general structure:
- Acknowledge the user's concern
- Offer preliminary information about possible causes
- Ask about symptom details (duration, severity, triggers)
- Inquire about related symptoms
- Ask if they've tried any treatments (including traditional remedies)
- Provide helpful advice while being clear about your limitations

Remember to:
- Format your responses in a natural, readable way
- Use short paragraphs with appropriate spacing between ideas
- Don't use markdown formatting like asterisks or numbered points
- Maintain a conversation flow rather than a clinical assessment"""
            
            # Add Nigerian Pidgin instructions if detected
            if has_pidgin:
                system_prompt += """
                The user is speaking Nigerian Pidgin. Respond in a mix of standard English and Nigerian Pidgin.
                Use natural Pidgin phrases without making the text too formal or structured.
                Common medical terms in Pidgin include:
                - "Belle pain" for stomach pain
                - "Dey purge" for diarrhea
                - "Fever dey worry me" for having a fever
                - "Body dey hot" for fever or high temperature
                - "I dey feel weak" for fatigue
                
                Speak in a warm, friendly tone as if you're talking to a friend. 
                Ask about local treatments like herbs or traditional medicine they might have used."""
            
            # Update the conversation with the user's new message
            langchain_messages = [SystemMessage(content=system_prompt)]
            
            # Add chat history
            for msg in messages:
                if msg.role == 'user':
                    langchain_messages.append(HumanMessage(content=msg.content))
                else:
                    langchain_messages.append(AIMessage(content=msg.content))
        
            # Add the current message
            langchain_messages.append(HumanMessage(content=message))
            
            # Log API key for debugging
            logger.info(f"API Key (first 5 chars): {os.getenv('OPENAI_API_KEY')[:5]}...")
            
            # Call the LLM
            llm = ChatOpenAI(model_name=self.model, temperature=0.7)
            response = llm.invoke(langchain_messages)
            
            # Get the response text
            reply = response.content
            
            # Save the interaction
            save_message(session, 'user', message)
            save_message(session, 'assistant', reply)
            
            logger.info(f"Received LLM response: {reply[:50]}...")
            
            return Response({'reply': reply})
        except Exception as e:
            logger.error(f"Error in ChatAPIView: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatSummaryAPIView(APIView):
    """Generate a summary of a conversation session for the doctor."""
    permission_classes = [AllowAny]
    def post(self, request):
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'No session_id provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the session object
        session = None
        
        # Handle string-based session IDs (e.g., 'session-xxxx')
        if isinstance(session_id, str) and session_id.startswith('session-'):
            # Find an existing session
            existing_sessions = ConversationSession.objects.all()
            if existing_sessions.exists():
                session = existing_sessions.first()
                logger.info(f"Using existing session for summary with string ID {session_id}")
            else:
                return Response({'error': 'No sessions found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Handle numeric session IDs
            try:
                session_id_int = int(session_id)
                try:
                    session = ConversationSession.objects.get(id=session_id_int)
                    logger.info(f"Found session for summary with ID {session_id_int}")
                except ConversationSession.DoesNotExist:
                    return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
                except ConversationSession.MultipleObjectsReturned:
                    # Handle multiple matches by using the first one
                    session = ConversationSession.objects.filter(id=session_id_int).first()
                    logger.info(f"Found multiple sessions with ID {session_id_int}, using first one for summary")
            except (ValueError, TypeError):
                # If conversion fails, use the first session
                session = ConversationSession.objects.first()
                if not session:
                    return Response({'error': 'No sessions found.'}, status=status.HTTP_404_NOT_FOUND)
                logger.info(f"Using first available session for summary with non-numeric ID {session_id}")
        
        # Get all messages from this session
        messages = session.messages.order_by('timestamp')
        
        if not messages:
            return Response({'error': 'No messages found in session.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Construct conversation text for summary
        conversation_text = ""
        
        # Aggregate all medical entities across the conversation
        all_entities = {}
        
        # Track patient emotions across the conversation
        patient_emotions = []
        
        for msg in messages:
            conversation_text += f"{msg.role.capitalize()}: {msg.content}\n\n"
            
            # Extract entities from user messages
            if msg.role == 'user':
                entities = extract_medical_entities(msg.content)
                for entity_type, words in entities.items():
                    if entity_type not in all_entities:
                        all_entities[entity_type] = set()
                    all_entities[entity_type].update(words)
                
                # Analyze emotion in each user message
                emotion_result = analyze_patient_emotion(msg.content)
                if emotion_result["emotion"] != "unknown":
                    patient_emotions.append(emotion_result)
        
        # Create a formatted string of all detected entities
        entity_summary = ""
        if all_entities:
            entity_summary = "Extracted medical entities:\n"
            
            # Format medications
            if "MEDICATION" in all_entities:
                entity_summary += f"- Medications: {', '.join(all_entities['MEDICATION'])}\n"
            
            # Format symptoms with attributes
            if "SYMPTOM" in all_entities:
                entity_summary += f"- Symptoms: {', '.join(all_entities['SYMPTOM'])}\n"
                
                # Add severity if available
                if "SEVERITY" in all_entities:
                    entity_summary += f"- Severity indicators: {', '.join(all_entities['SEVERITY'])}\n"
                
                # Add duration if available
                if "DURATION" in all_entities:
                    entity_summary += f"- Duration information: {', '.join(all_entities['DURATION'])}\n"
            
            # Format conditions
            if "CONDITION" in all_entities:
                entity_summary += f"- Medical conditions: {', '.join(all_entities['CONDITION'])}\n"
                
            # Format vital signs
            if "VITALS" in all_entities:
                entity_summary += f"- Vital signs: {', '.join(all_entities['VITALS'])}\n"
        
        # Create a summary of patient emotions
        emotion_summary = ""
        if patient_emotions:
            emotion_counts = {}
            for emotion_data in patient_emotions:
                emotion = emotion_data["emotion"]
                if emotion not in emotion_counts:
                    emotion_counts[emotion] = 0
                emotion_counts[emotion] += 1
            
            # Get the dominant emotion
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
            emotion_summary = f"Patient emotional state: Patient predominantly expressed {dominant_emotion}. "
            
            # Add emotional state details
            emotion_percentages = {emotion: (count / len(patient_emotions)) * 100 
                                for emotion, count in emotion_counts.items()}
            emotion_list = [f"{emotion} ({percentage:.0f}%)" for emotion, percentage in emotion_percentages.items()]
            emotion_summary += f"Emotions detected during conversation: {', '.join(emotion_list)}."
        
        # Create a summary using LangChain
        # Configure a clinical summarizer with focus and clarity
        llm = ChatOpenAI(
            temperature=0.4,  # Very structured and safe
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            model="gpt-4o",
            model_kwargs={
                "top_p": 0.85
            }
        )

        # Refined summary prompt
        summary_template = """
        You are a medical documentation assistant. Based on the following conversation between a patient and a virtual healthcare assistant, generate a clinical summary for a doctor.

        ---

        Conversation:
        {conversation}

        ---

        Detected Medical Entities:
        {entity_summary}

        Patient Emotional Overview:
        {emotion_summary}

        ---

        Your summary must include:
        1. **Patient's main symptoms** (with severity and duration if mentioned)
        2. **Relevant medical conditions or history**
        3. **Any medications, treatments, or vital signs referenced**
        4. **Patient's emotional state during the conversation**
        5. **Any lifestyle or contextual clues (e.g. sleep, stress, work)**
        6. **Questions or concerns raised by the patient**
        7. **Suggested next steps or further assessments if applicable**

        Format your output clearly. Aim for 5–8 sentences that a doctor could quickly read before consultation.
        """

        summary_prompt = PromptTemplate(
            input_variables=["conversation", "entity_summary", "emotion_summary"],
            template=summary_template
        )

        summary_chain = LLMChain(llm=llm, prompt=summary_prompt)
        
        try:
            summary = summary_chain.run(
                conversation=conversation_text, 
                entity_summary=entity_summary,
                emotion_summary=emotion_summary
            )
            
            return Response({
                'summary': summary,
                'session_id': session_id,
                'extracted_entities': {k: list(v) for k, v in all_entities.items()} if all_entities else {},
                'emotional_analysis': {
                    'dominant_emotion': dominant_emotion if patient_emotions else "unknown",
                    'emotion_breakdown': emotion_percentages if patient_emotions else {}
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FeedbackAPIView(APIView):
    """Handle feedback submissions from users"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Save user feedback on AI responses"""
        session_id = request.data.get('session_id')
        rating = request.data.get('rating')
        culturally_appropriate = request.data.get('culturally_appropriate', True)
        comment = request.data.get('comment', '')
        user_query = request.data.get('user_query', '')
        response_text = request.data.get('response_text', '')
        
        if not session_id:
            return Response({'error': 'No session_id provided'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return Response({'error': 'Invalid rating provided. Must be an integer from 1-5'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the conversation session
            session = get_or_create_conversation_session(session_id)
            
            # Create the feedback record
            from .models import Feedback
            feedback = Feedback.objects.create(
                session=session,
                rating=rating,
                culturally_appropriate=culturally_appropriate,
                comment=comment,
                user_query=user_query,
                response_text=response_text
            )
            
            logger.info(f"Feedback saved: Rating {rating}/5 for session {session_id}")
            
            return Response({
                'status': 'success',
                'message': 'Feedback saved successfully',
                'feedback_id': feedback.id
            })
            
        except Exception as e:
            logger.error(f"Error saving feedback: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserContextAPIView(APIView):
    """API for managing user medical context throughout a conversation."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get the user context for a specific session."""
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': 'No session_id provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = get_or_create_conversation_session(session_id)
        
        try:
            context = UserContext.objects.get(session=session)
            serializer = UserContextSerializer(context)
            return Response(serializer.data)
        except UserContext.DoesNotExist:
            # Create a new empty context
            context = UserContext.objects.create(session=session)
            serializer = UserContextSerializer(context)
            return Response(serializer.data)
            
    def post(self, request):
        """Create or update user context."""
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'No session_id provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = get_or_create_conversation_session(session_id)
        
        # Try to get existing context or create new one
        context, created = UserContext.objects.get_or_create(session=session)
        
        # Update fields based on request data
        if 'symptoms' in request.data:
            # Merge the symptoms instead of replacing
            current_symptoms = context.symptoms or {}
            new_symptoms = request.data.get('symptoms', {})
            context.symptoms = {**current_symptoms, **new_symptoms}
            
        if 'symptom_durations' in request.data:
            current_durations = context.symptom_durations or {}
            new_durations = request.data.get('symptom_durations', {})
            context.symptom_durations = {**current_durations, **new_durations}
            
        if 'treatments_tried' in request.data:
            current_treatments = context.treatments_tried or []
            new_treatments = request.data.get('treatments_tried', [])
            # Add only unique treatments
            for treatment in new_treatments:
                if treatment not in current_treatments:
                    current_treatments.append(treatment)
            context.treatments_tried = current_treatments
            
        if 'medical_history' in request.data:
            current_history = context.medical_history or []
            new_history = request.data.get('medical_history', [])
            # Add only unique history items
            for item in new_history:
                if item not in current_history:
                    current_history.append(item)
            context.medical_history = current_history
            
        if 'cultural_preferences' in request.data:
            current_preferences = context.cultural_preferences or {}
            new_preferences = request.data.get('cultural_preferences', {})
            context.cultural_preferences = {**current_preferences, **new_preferences}
            
        if 'language' in request.data:
            context.language = request.data.get('language')
            
        context.save()
        
        serializer = UserContextSerializer(context)
        return Response(serializer.data)
        
    def patch(self, request):
        """Update specific fields of user context."""
        return self.post(request)  # Reuse post logic for partial updates


class ExpertReviewAPIView(APIView):
    """API for managing expert reviews of AI responses."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get expert reviews for a specific feedback ID or list all."""
        feedback_id = request.query_params.get('feedback_id')
        
        if feedback_id:
            reviews = ExpertReview.objects.filter(feedback_id=feedback_id)
        else:
            reviews = ExpertReview.objects.all().order_by('-created_at')[:50]  # Limit to 50 most recent
            
        serializer = ExpertReviewSerializer(reviews, many=True)
        return Response(serializer.data)
        
    def post(self, request):
        """Create a new expert review."""
        serializer = ExpertReviewSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnalyticsAPIView(APIView):
    """API for generating and retrieving analytics data."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get analytics metrics with optional date filtering."""
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        metric_type = request.query_params.get('metric_type')
        
        # Build query filter
        query_filter = {}
        if from_date:
            query_filter['date__gte'] = from_date
        if to_date:
            query_filter['date__lte'] = to_date
        if metric_type:
            query_filter['metric_type'] = metric_type
            
        # Get the metrics
        metrics = AnalyticsMetric.objects.filter(**query_filter).order_by('date', 'metric_type')
        serializer = AnalyticsMetricSerializer(metrics, many=True)
        return Response(serializer.data)
        
    def post(self, request):
        """Generate analytics metrics for a specific date range."""
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        
        if not from_date or not to_date:
            return Response({'error': 'Both from_date and to_date are required.'}, 
                            status=status.HTTP_400_BAD_REQUEST)
                            
        # Generate the analytics data for the date range
        try:
            self.generate_metrics(from_date, to_date)
            return Response({'status': 'Analytics metrics generated successfully.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_metrics(self, from_date, to_date):
        """Generate metrics for the specified date range."""
        from django.db.models import Avg, Count
        from django.db.models.functions import TruncDate
        import datetime
        
        # Convert string dates to datetime objects if necessary
        if isinstance(from_date, str):
            from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
        if isinstance(to_date, str):
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
        
        # Generate average rating metrics
        avg_ratings = Feedback.objects.filter(created_at__date__gte=from_date, 
                                            created_at__date__lte=to_date) \
                                     .annotate(date=TruncDate('created_at')) \
                                     .values('date') \
                                     .annotate(avg_rating=Avg('rating')) \
                                     .order_by('date')
                                     
        for rating_data in avg_ratings:
            # Save or update the metric
            AnalyticsMetric.objects.update_or_create(
                metric_type='avg_rating',
                date=rating_data['date'],
                defaults={'value': rating_data['avg_rating']}
            )
            
        # Generate cultural appropriateness score
        cultural_scores = Feedback.objects.filter(created_at__date__gte=from_date,
                                                created_at__date__lte=to_date) \
                                         .annotate(date=TruncDate('created_at')) \
                                         .values('date') \
                                         .annotate(
                                             culturally_appropriate_pct=Avg(
                                                 models.Case(
                                                     models.When(culturally_appropriate=True, then=100),
                                                     default=0,
                                                     output_field=models.FloatField()
                                                 )
                                             )
                                         ) \
                                         .order_by('date')
                                         
        for score_data in cultural_scores:
            AnalyticsMetric.objects.update_or_create(
                metric_type='cultural_score',
                date=score_data['date'],
                defaults={'value': score_data['culturally_appropriate_pct']}
            )
            
        # Generate feedback count metrics
        feedback_counts = Feedback.objects.filter(created_at__date__gte=from_date,
                                                created_at__date__lte=to_date) \
                                         .annotate(date=TruncDate('created_at')) \
                                         .values('date') \
                                         .annotate(count=Count('id')) \
                                         .order_by('date')
                                         
        for count_data in feedback_counts:
            AnalyticsMetric.objects.update_or_create(
                metric_type='feedback_count',
                date=count_data['date'],
                defaults={'value': count_data['count']}
            )
        
        # Generate expert review metrics if available
        if ExpertReview.objects.exists():
            expert_ratings = ExpertReview.objects.filter(created_at__date__gte=from_date,
                                                      created_at__date__lte=to_date) \
                                               .annotate(date=TruncDate('created_at')) \
                                               .values('date') \
                                               .annotate(
                                                   avg_accuracy=Avg('medical_accuracy'),
                                                   avg_relevance=Avg('cultural_relevance')
                                               ) \
                                               .order_by('date')
                                               
            for expert_data in expert_ratings:
                # Medical accuracy metric
                AnalyticsMetric.objects.update_or_create(
                    metric_type='medical_accuracy',
                    date=expert_data['date'],
                    defaults={'value': expert_data['avg_accuracy']}
                )
                
                # Cultural relevance metric
                AnalyticsMetric.objects.update_or_create(
                    metric_type='cultural_relevance',
                    date=expert_data['date'],
                    defaults={'value': expert_data['avg_relevance']}
                )


class AnalyticsDashboardAPIView(APIView):
    """API for dashboard-specific analytics that provides aggregated metrics."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get dashboard metrics with various aggregations."""
        from django.db.models import Avg, Count, Max, Min
        from django.utils import timezone
        import datetime
        
        # Default to last 30 days if no date range specified
        to_date = timezone.now().date()
        from_date = to_date - datetime.timedelta(days=30)
        
        # Override with query parameters if provided
        if 'from_date' in request.query_params:
            from_date = datetime.datetime.strptime(
                request.query_params.get('from_date'), '%Y-%m-%d'
            ).date()
        if 'to_date' in request.query_params:
            to_date = datetime.datetime.strptime(
                request.query_params.get('to_date'), '%Y-%m-%d'
            ).date()
            
        # Get overall metrics
        overall_metrics = {}
        
        # Average rating
        avg_rating = Feedback.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        ).aggregate(avg=Avg('rating'))
        overall_metrics['avg_rating'] = avg_rating['avg'] or 0
        
        # Cultural appropriateness percentage
        cultural_appropriate_count = Feedback.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
            culturally_appropriate=True
        ).count()
        
        total_feedback_count = Feedback.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        ).count()
        
        if total_feedback_count > 0:
            cultural_score = (cultural_appropriate_count / total_feedback_count) * 100
        else:
            cultural_score = 0
            
        overall_metrics['cultural_score'] = cultural_score
        overall_metrics['feedback_count'] = total_feedback_count
        
        # Get time series data
        time_series = {}
        
        # Get all analytics metrics
        metrics = AnalyticsMetric.objects.filter(
            date__gte=from_date,
            date__lte=to_date
        ).order_by('date', 'metric_type')
        
        for metric in metrics:
            if metric.metric_type not in time_series:
                time_series[metric.metric_type] = []
                
            time_series[metric.metric_type].append({
                'date': metric.date.isoformat(),
                'value': metric.value,
                'text_value': metric.text_value
            })
            
        # Return both overall and time series data
        return Response({
            'overall': overall_metrics,
            'time_series': time_series,
            'date_range': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            }
        })

class DataPipelineView(APIView):
    """
    API for data pipeline operations related to feedback processing and model training data
    """
    permission_classes = [AllowAny]  # Adjust as needed for production
    
    def get(self, request):
        """Get pipeline statistics and available datasets"""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        # Check if the directory exists
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            
        # Get list of available training datasets
        datasets = []
        for file in os.listdir(data_dir):
            if file.startswith('training_data_') and file.endswith('.json'):
                file_path = os.path.join(data_dir, file)
                datasets.append({
                    'filename': file,
                    'size': os.path.getsize(file_path),
                    'created': datetime.datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                    'path': file_path
                })
                
        # Get latest metrics
        latest_metrics = AnalyticsMetric.objects.all().order_by('-date')[:10]
        metrics_data = [
            {
                'id': metric.id,
                'type': metric.metric_type,
                'date': metric.date.isoformat(),
                'value': metric.value,
                'text_value': metric.text_value
            }
            for metric in latest_metrics
        ]
        
        return Response({
            'datasets': datasets,
            'latest_metrics': metrics_data
        })
        
    def post(self, request):
        """Run data pipeline operations based on request data"""
        operation = request.data.get('operation')
        
        if not operation:
            return Response({'error': 'No operation specified'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Parse date parameters
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        
        if from_date:
            try:
                from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid from_date format. Use YYYY-MM-DD'}, 
                                status=status.HTTP_400_BAD_REQUEST)
                                
        if to_date:
            try:
                to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid to_date format. Use YYYY-MM-DD'}, 
                                status=status.HTTP_400_BAD_REQUEST)
        
        # Update metrics operation
        if operation == 'update_metrics':
            result = process_and_update_metrics(from_date, to_date)
            return Response(result)
            
        # Generate training data operation
        elif operation == 'generate_training':
            min_rating = request.data.get('min_rating')
            if min_rating:
                try:
                    min_rating = int(min_rating)
                    if min_rating < 1 or min_rating > 5:
                        return Response({'error': 'min_rating must be between 1 and 5'}, 
                                        status=status.HTTP_400_BAD_REQUEST)
                except ValueError:
                    return Response({'error': 'min_rating must be an integer'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
            
            result = generate_training_data(from_date, to_date, min_rating)
            return Response(result)
            
        # Unknown operation
        else:
            return Response({'error': f'Unknown operation: {operation}'}, 
                            status=status.HTTP_400_BAD_REQUEST)
