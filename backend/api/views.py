from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Task
from .serializers import TaskSerializer
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

from .models import ConversationSession, Message
from .medical_ner import extract_medical_entities, analyze_patient_emotion
import logging

# Set up logging
logger = logging.getLogger(__name__)

def is_pure_pidgin(text):
    pidgin_keywords = [
        "bele", "wahala", "dey", "go", "no worry", "abeg", "small-small",
        "pain me", "comot", "gist", "how far", "na", "wetin", "palava", "waka"
    ]
    return any(word in text.lower() for word in pidgin_keywords)

# Create your views here.

# Load environment variables from .env
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by('-created_at')
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]  # For development, restrict in production

class ChatAPIView(APIView):
    """Handle chat messages: save user message, get LangChain to generate a response using chat memory."""
    permission_classes = [AllowAny]
    def post(self, request):
        user_message = request.data.get('message')
        session_id = request.data.get('session_id')
        logger.info(f"Received chat request: message={user_message}, session_id={session_id}")
        
        if not user_message:
            return Response({'error': 'No message provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve or create session
        if session_id:
            session = get_object_or_404(ConversationSession, id=session_id)
        else:
            session = ConversationSession.objects.create()
            welcome_message = "Hello! I'm Elara, your virtual healthcare assistant. How are you feeling today, and what would you like to discuss regarding your health?"
            Message.objects.create(session=session, role='assistant', content=welcome_message)
            return Response({
                'reply': welcome_message,
                'session_id': session.id,
                'entities': {},
                'emotion': {}
            })

        # Extract medical entities from user message
        detected_entities = extract_medical_entities(user_message)
        logger.info(f"Detected medical entities: {detected_entities}")
        
        # Analyze patient emotion
        emotion_result = analyze_patient_emotion(user_message)
        logger.info(f"Detected patient emotion: {emotion_result}")

        # Save user message to database
        Message.objects.create(session=session, role='user', content=user_message)

        # Create LangChain's ChatOpenAI instance
        # Dynamically adjust LLM temperature based on patient emotion
        emotion = emotion_result.get("emotion", "unknown")
        if emotion in ["joy", "neutral"]:
            temp_setting = 1.3  # More expressive, human
        elif emotion in ["sadness", "fear"]:
            temp_setting = 0.8  # Gentle and supportive
        else:
            temp_setting = 1.0  # Balanced

        # Initialize conversational LLM with creative but controlled settings
        llm = ChatOpenAI(
            temperature=temp_setting,
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            model="gpt-4o",
            model_kwargs={
                "top_p": 0.95  # Wide but not too chaotic   # Still grounded in quality
            }
        )
        
        # Load previous messages from database for this session
        history = session.messages.order_by('timestamp')
        
        # Pidgin vs Standard tone switch
        if is_pure_pidgin(user_message):
            system_message = (
                "You be Elara, na smart and kind healthcare assistant wey sabi speak Nigerian Pidgin well. "
                "Talk like say you dey gist with person, but still give solid medical help. "
                "Greet the person well, ask wetin dey do dem, find out how long the thing don dey, "
                "and if dem don try anything. If e no serious, give small advice. If e serious, summarize the problem. "
                "No form, no English overload — just make dem feel say you dey for their side."
            )
        else:
            system_message = (
                "You are Elara, a warm and compassionate AI assistant designed to help patients with their inquiries. "
                "Begin by greeting the patient warmly to create a comfortable atmosphere. Then, ask them about their "
                "symptoms in detail. Follow up with further questions related to their lifestyle and any other relevant "
                "factors that might be connected to their complained issue. Assess the severity of the issue based on "
                "their responses. If the issue appears non-critical, offer gentle and supportive advice on what steps "
                "they can take next. If the issue seems critical or urgent, generate a clear and concise summary of the "
                "patient's concerns and symptoms for further medical attention. Maintain empathy and clarity throughout the interaction."
            )
        
        # Add entity awareness to system prompt if entities were detected
        if detected_entities:
            # Format structured medical entities for prompt
            entity_sections = []
            
            if "MEDICATION" in detected_entities:
                entity_sections.append(f"MEDICATIONS: {', '.join(detected_entities['MEDICATION'])}")
            
            if "SYMPTOM" in detected_entities:
                entity_sections.append(f"SYMPTOMS: {', '.join(detected_entities['SYMPTOM'])}")
                
                # Add symptom attributes if available
                if "SEVERITY" in detected_entities:
                    entity_sections.append(f"SEVERITY: {', '.join(detected_entities['SEVERITY'])}")
                
                if "DURATION" in detected_entities:
                    entity_sections.append(f"DURATION: {', '.join(detected_entities['DURATION'])}")
            
            if "CONDITION" in detected_entities:
                entity_sections.append(f"CONDITIONS: {', '.join(detected_entities['CONDITION'])}")
                
            if "VITALS" in detected_entities:
                entity_sections.append(f"VITALS: {', '.join(detected_entities['VITALS'])}")
            
            entity_text = "; ".join(entity_sections)
            system_message += f"\n\nThe patient has mentioned these medical entities: {entity_text}. Ask specific follow-up questions about these findings, their severity, duration, and any other relevant details."
            
            # Add clinical guidance based on detected entities
            if "CONDITION" in detected_entities:
                system_message += "\n\nAsk questions specific to the mentioned conditions, focusing on symptoms, medications, and how they're managing these conditions."
                
            if "VITALS" in detected_entities:
                system_message += "\n\nPay attention to the vitals mentioned and inquire further about any abnormal values."
                
            if "MEDICATION" in detected_entities:
                system_message += "\n\nAsk about medication adherence, effectiveness, and any side effects they might be experiencing."
        
        # Add emotion awareness
        if emotion_result["emotion"] != "unknown":
            system_message += f"\n\nThe patient appears to be feeling {emotion_result['emotion']} (confidence: {emotion_result['confidence']:.2f}). "
            
            # Add specific guidance based on detected emotion
            if emotion_result["emotion"] == "sadness" or emotion_result["emotion"] == "fear":
                system_message += "Show empathy and reassurance in your response. Ask gently about how they're coping emotionally."
            elif emotion_result["emotion"] == "anger":
                system_message += "Acknowledge their frustration and respond calmly. Try to understand what might be causing their distress."
            elif emotion_result["emotion"] == "joy":
                system_message += "Acknowledge their positive state while still addressing their medical concerns professionally."
        
        # Initialize conversation with previous messages from database
        # Convert our database messages to LangChain message format
        langchain_messages = [SystemMessage(content=system_message)]
        
        for msg in history:
            if msg.role == 'user':
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == 'assistant':
                langchain_messages.append(AIMessage(content=msg.content))
        
        try:
            # Get response from language model
            logger.info(f"Sending {len(langchain_messages)} messages to LLM")
            logger.info(f"Messages: {langchain_messages}")
            logger.info(f"API Key (first 5 chars): {os.getenv('OPENAI_API_KEY')[:5]}...")
            response = llm(langchain_messages)
            assistant_reply = response.content
            logger.info(f"Received LLM response: {assistant_reply[:50]}...")
            
            # Save assistant message to database
            Message.objects.create(session=session, role='assistant', content=assistant_reply)
            
            return Response({
                'reply': assistant_reply,
                'session_id': session.id,
                'entities': detected_entities,
                'emotion': emotion_result
            })
            
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
        
        try:
            session = ConversationSession.objects.get(id=session_id)
        except ConversationSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        
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
