import React, { useState, useEffect, useRef } from 'react';
import { RoomAudioRenderer } from '@livekit/components-react';
import '@livekit/components-styles';
import './VoiceChat.css';
import LanguageSelector from './LanguageSelector';
import VoiceSelector from './VoiceSelector';

// Import the LiveKit components properly
const LiveKitRoom = React.lazy(() => import('@livekit/components-react').then(module => ({ 
  default: module.LiveKitRoom 
})));

// Environment variables or fallback to localhost
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

// Default welcome messages by language
const WELCOME_MESSAGES: {[key: string]: string} = {
  "en": "Hello, I'm your EleraAI healthcare assistant. How can I help you today?",
  "en-pidgin": "Hello! I be your EleraAI healthcare assistant. How I fit help you today?",
  "yo": "Bawo ni, Emi ni iranlowo ilera EleraAI re. Bawo ni mo se le ran o lowo loni?",
  "ig": "Kedu, abụ m onye nkwado ahụike EleraAI gị. Kedu ka m ga-esi nyere gị aka taa?",
  "ha": "Sannu, ni ne mai'aikacin kula da lafiya na EleraAI. Yaya zan iya taimake ka yau?",
  "fr": "Bonjour, je suis votre assistant de santé EleraAI. Comment puis-je vous aider aujourd'hui?",
  "es": "Hola, soy su asistente de salud EleraAI. ¿Cómo puedo ayudarle hoy?",
};

// Feedback interface
interface Feedback {
  rating: number | null;
  culturallyAppropriate: boolean;
  comment: string;
}

interface VoiceChatProps {
  conversationId: string;
  userName: string;
  onTranscriptUpdate?: (transcript: string) => void;
  welcomeMessage?: string;
}

const VoiceChat: React.FC<VoiceChatProps> = ({ 
  conversationId, 
  userName, 
  onTranscriptUpdate,
  welcomeMessage
}) => {
  const [token, setToken] = useState<string>('');
  const [roomName, setRoomName] = useState<string>('');
  const [livekitUrl, setLivekitUrl] = useState<string>('');
  const [voiceSessionId, setVoiceSessionId] = useState<number | null>(null);
  const [participantId, setParticipantId] = useState<number | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [assistantResponse, setAssistantResponse] = useState<string>('');
  const [isAssistantSpeaking, setIsAssistantSpeaking] = useState<boolean>(false);
  const [hasMicPermission, setHasMicPermission] = useState<boolean | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  const [selectedVoice, setSelectedVoice] = useState<string>('CJsvtXkl6ObQJrCz44le');
  const [showVoiceLimitWarning, setShowVoiceLimitWarning] = useState<boolean>(false);
  const [continuousMode, setContinuousMode] = useState<boolean>(true);
  const [hasPlayedWelcome, setHasPlayedWelcome] = useState<boolean>(false);
  const [showFeedback, setShowFeedback] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<Feedback>({
    rating: null,
    culturallyAppropriate: true,
    comment: ''
  });

  // Audio recording state
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const isRecordingRef = useRef<boolean>(false);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const silenceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const hasPlayedWelcomeRef = useRef<boolean>(false);

  useEffect(() => {
    // Check microphone permissions on component mount
    checkMicrophonePermission();
    
    // Get token from the backend when component mounts
    const fetchToken = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/voice/token/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            conversation_id: conversationId,
            user_identity: `user-${conversationId}`,
            user_name: userName,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to get token: ${response.status}`);
        }

        const data = await response.json();
        setToken(data.token);
        setRoomName(data.room_name);
        setLivekitUrl(data.livekit_url);
        setVoiceSessionId(data.voice_session_id);
        setParticipantId(data.participant_id);
      } catch (err) {
        console.error('Error fetching token:', err);
        setError('Failed to connect to voice service. Please try again.');
      }
    };

    fetchToken();
    
    // Cleanup function to stop any recording when component unmounts
    return () => {
      stopRecording();
      
      // Clean up audio context
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
      
      // Clean up silence detection
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
        silenceTimeoutRef.current = null;
      }
      
      // Clean up animation frame
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [conversationId, userName]);
  
  // Check microphone permission
  const checkMicrophonePermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      setHasMicPermission(true);
      // Don't stop the stream here as we might need it later
    } catch (err) {
      console.error('Microphone permission denied:', err);
      setHasMicPermission(false);
      setError('Microphone access denied. Please allow microphone access to use voice chat.');
    }
  };

  // Function to request microphone permissions
  const requestMicrophonePermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      setHasMicPermission(true);
      setError(null);
    } catch (err) {
      console.error('Failed to get microphone permission:', err);
      setHasMicPermission(false);
      setError('Microphone access denied. Please allow microphone access in your browser settings.');
    }
  };

  // Function to detect silence
  const detectSilence = () => {
    if (!analyserRef.current || !dataArrayRef.current) return;
    
    analyserRef.current.getByteFrequencyData(dataArrayRef.current);
    
    // Calculate average volume
    const average = dataArrayRef.current.reduce((a, b) => a + b, 0) / dataArrayRef.current.length;
    
    // If volume is below threshold, start silence timeout
    if (average < 10) { // Lower threshold for better silence detection
      if (!silenceTimeoutRef.current) {
        silenceTimeoutRef.current = setTimeout(() => {
          console.log('Silence detected, stopping recording');
          stopRecording();
        }, 1000); // Reduced to 1 second for faster response
      }
    } else {
      // If there's sound, clear the timeout
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
        silenceTimeoutRef.current = null;
      }
    }
    
    // Continue checking if still recording
    if (isRecordingRef.current) {
      animationFrameRef.current = requestAnimationFrame(detectSilence);
    }
  };

  // Function to start recording audio
  const startRecording = async () => {
    if (isRecordingRef.current) return;
    
    try {
      // Clean up any previous instances first
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
      
      // Use existing stream if available, otherwise request a new one
      let stream = audioStreamRef.current;
      if (!stream) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioStreamRef.current = stream;
      }
      
      // Set up AudioContext for silence detection
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      
      source.connect(analyser);
      analyser.fftSize = 256;
      
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      dataArrayRef.current = dataArray;
      
      const mediaRecorder = new MediaRecorder(stream);
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        // Cancel any pending silence detection
        if (silenceTimeoutRef.current) {
          clearTimeout(silenceTimeoutRef.current);
          silenceTimeoutRef.current = null;
        }
        
        // Cancel animation frame
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
          animationFrameRef.current = null;
        }
        
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await transcribeAudio(audioBlob);
        audioChunksRef.current = [];
        
        // Ensure we're ready for the next recording
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
          audioContextRef.current.close();
          audioContextRef.current = null;
        }
      };
      
      mediaRecorder.start(500); // Collect data in 0.5-second chunks for more responsive behavior
      isRecordingRef.current = true;
      setIsSpeaking(true);
      
      // Start silence detection
      animationFrameRef.current = requestAnimationFrame(detectSilence);
      
      console.log('Recording started with silence detection');
      
      // Play welcome message first if this is the first time
      // Use both state and ref to ensure welcome message only plays once
      if (!hasPlayedWelcome && !hasPlayedWelcomeRef.current && voiceSessionId) {
        await playWelcomeMessage();
      }
    } catch (err) {
      console.error('Error starting recording:', err);
      setError('Failed to access microphone. Please check your browser permissions.');
      setHasMicPermission(false);
    }
  };

  // Play welcome message
  const playWelcomeMessage = async () => {
    if (!voiceSessionId || hasPlayedWelcomeRef.current) return;
    
    try {
      // Set ref immediately to prevent any possibility of duplicate calls
      hasPlayedWelcomeRef.current = true;
      
      // Stop recording temporarily while playing welcome message
      if (isRecordingRef.current) {
        stopRecording();
      }
      
      setIsAssistantSpeaking(true);
      
      // Get appropriate welcome message
      const message = welcomeMessage || WELCOME_MESSAGES[selectedLanguage] || WELCOME_MESSAGES["en"];
      setAssistantResponse(message);
      
      // Synthesize welcome message
      await synthesizeSpeech(message, true); // Pass true to indicate this is the welcome message
      
      // Update state after message is played
      setHasPlayedWelcome(true);
    } catch (err) {
      console.error('Error playing welcome message:', err);
      setIsAssistantSpeaking(false);
      
      // If welcome message fails, still mark as played to avoid retry loops
      setHasPlayedWelcome(true);
      
      // Start recording even if welcome message fails
      setTimeout(() => {
        startRecording();
      }, 500);
    }
  };

  // Function to stop recording audio
  const stopRecording = () => {
    if (!isRecordingRef.current) return;
    
    console.log('Stopping recording and cleaning up resources');
    
    // Clean up silence detection
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
    
    // Clean up animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    
    // Stop the media recorder if it exists and is recording
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (err) {
        console.error('Error stopping media recorder:', err);
      }
    }
    
    isRecordingRef.current = false;
    setIsSpeaking(false);
  };

  // Function to transcribe audio using the backend API
  const transcribeAudio = async (audioBlob: Blob) => {
    if (!voiceSessionId) return;
    
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('voice_session_id', voiceSessionId.toString());
      if (participantId) {
        formData.append('participant_id', participantId.toString());
      }
      formData.append('language', selectedLanguage);
      
      const response = await fetch(`${BACKEND_URL}/voice/transcribe/`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`Failed to transcribe audio: ${response.status}`);
      }
      
      const data = await response.json();
      setTranscript(data.transcript);
      
      // Notify parent component about transcript update
      if (onTranscriptUpdate) {
        onTranscriptUpdate(data.transcript);
      }
      
      // Process transcript with AI and get response
      await processTranscriptAndSpeak(data.transcript);
      
    } catch (err) {
      console.error('Error transcribing audio:', err);
    }
  };

  // Function to process transcript and get AI response
  const processTranscriptAndSpeak = async (text: string) => {
    if (!voiceSessionId || !text.trim()) return;
    
    try {
      // First, send transcript to the chat API to get AI response
      const chatResponse = await fetch(`${BACKEND_URL}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          session_id: conversationId,
        }),
      });
      
      if (!chatResponse.ok) {
        throw new Error(`Failed to get AI response: ${chatResponse.status}`);
      }
      
      const chatData = await chatResponse.json();
      const aiResponse = chatData.reply;
      
      setAssistantResponse(aiResponse);
      
      // Reset feedback state and show feedback UI after response
      setFeedback({
        rating: null,
        culturallyAppropriate: true,
        comment: ''
      });
      setShowFeedback(true);
      
      // Then, use TTS to synthesize speech
      await synthesizeSpeech(aiResponse);
      
    } catch (err) {
      console.error('Error processing transcript:', err);
    }
  };

  // Function to synthesize speech using the backend API
  const synthesizeSpeech = async (text: string, isWelcomeMessage = false) => {
    if (!voiceSessionId || !text.trim()) return;
    
    try {
      setIsAssistantSpeaking(true);
      
      const response = await fetch(`${BACKEND_URL}/voice/synthesize/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          voice_session_id: voiceSessionId,
          text: text,
          language_code: selectedLanguage,
          voice_id: selectedVoice || undefined,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        // Check if this is a voice limit error
        if (errorData.detail && errorData.detail.status === 'voice_limit_reached') {
          setShowVoiceLimitWarning(true);
          // Fall back to the African voice that works on free tier
          setSelectedVoice('jsCqWAovK2LkecY7zXl4');
          // Try again with the fallback voice
          return synthesizeSpeech(text, isWelcomeMessage);
        }
        throw new Error(`Failed to synthesize speech: ${response.status}`);
      }
      
      // Voice worked, so hide warning if it was showing
      setShowVoiceLimitWarning(false);
      
      // Play the audio
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setIsAssistantSpeaking(false);
        URL.revokeObjectURL(audioUrl);
        
        // For welcome message or if continuous mode is on, start recording automatically
        if (isWelcomeMessage || continuousMode) {
          setTimeout(() => {
            startRecording();
          }, 500); // Small delay to ensure UI updates before recording starts
        }
      };
      
      audio.play();
      
    } catch (err) {
      console.error('Error synthesizing speech:', err);
      setIsAssistantSpeaking(false);
      // If we have an error that couldn't be automatically handled above,
      // show the warning as a fallback
      setShowVoiceLimitWarning(true);
      
      // Start recording even if there was an error, but only for welcome message
      if (isWelcomeMessage) {
        setTimeout(() => {
          startRecording();
        }, 500);
      }
    }
  };

  // Handle language change
  const handleLanguageChange = (language: string) => {
    setSelectedLanguage(language);
  };

  // Handle voice change
  const handleVoiceChange = (voiceId: string) => {
    setSelectedVoice(voiceId);
  };

  // Handle room events
  const handleRoomEvents = () => {
    setIsConnected(true);
    console.log('Room connected successfully');
  };

  // Handle feedback submission
  const submitFeedback = async () => {
    if (!feedback.rating) return;
    
    try {
      // Send feedback to the backend
      const response = await fetch(`${BACKEND_URL}/api/feedback/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: conversationId,
          rating: feedback.rating,
          culturally_appropriate: feedback.culturallyAppropriate,
          comment: feedback.comment,
          response_text: assistantResponse,
          user_query: transcript
        }),
      }).catch(err => {
        // Silently fail if the endpoint doesn't exist yet
        console.log('Feedback endpoint not implemented yet:', err);
        return null;
      });
      
      if (response && response.ok) {
        console.log('Feedback submitted successfully');
      }
    } catch (err) {
      console.error('Error submitting feedback:', err);
      // Fail silently - don't interrupt the user experience
    } finally {
      // Hide the feedback form
      setShowFeedback(false);
    }
  };

  // Feedback component
  const FeedbackComponent = () => {
    if (!showFeedback) return null;
    
    return (
      <div className="feedback-container">
        <h4>How was my response?</h4>
        <div className="star-rating">
          {[1, 2, 3, 4, 5].map(star => (
            <span 
              key={star} 
              className={`star ${feedback.rating && feedback.rating >= star ? 'active' : ''}`}
              onClick={() => setFeedback({...feedback, rating: star})}
            >
              ★
            </span>
          ))}
        </div>
        <div className="cultural-check">
          <label>
            <input 
              type="checkbox" 
              checked={feedback.culturallyAppropriate} 
              onChange={() => setFeedback({...feedback, culturallyAppropriate: !feedback.culturallyAppropriate})}
            />
            Culturally appropriate
          </label>
        </div>
        <textarea 
          placeholder="Additional comments (optional)" 
          value={feedback.comment}
          onChange={(e) => setFeedback({...feedback, comment: e.target.value})}
        />
        <div className="feedback-buttons">
          <button onClick={() => setShowFeedback(false)}>Skip</button>
          <button 
            className="submit-feedback" 
            onClick={submitFeedback}
            disabled={!feedback.rating}
          >
            Submit
          </button>
        </div>
      </div>
    );
  };

  // Button to toggle speaking
  const SpeakButton = () => {
    const handleSpeakToggle = () => {
      if (isSpeaking) {
        stopRecording();
      } else {
        startRecording();
      }
    };
    
    // If microphone permission is denied, show a button to request it
    if (hasMicPermission === false) {
      return (
        <button 
          className="speak-button permission-button"
          onClick={requestMicrophonePermission}
        >
          Enable Microphone
        </button>
      );
    }
    
    return (
      <button 
        className={`speak-button ${isSpeaking ? 'speaking' : ''} ${isAssistantSpeaking ? 'disabled' : ''}`}
        onClick={handleSpeakToggle}
        disabled={isAssistantSpeaking}
      >
        {isSpeaking ? (
          <>
            <span className="pulse-recording"></span>
            Listening... (auto-stops after silence)
          </>
        ) : continuousMode ? 'Tap to Start Conversation' : 'Tap to Speak'}
      </button>
    );
  };

  if (error) {
    return (
      <div className="voice-chat-error">
        {error}
        {hasMicPermission === false && (
          <button 
            className="permission-button"
            onClick={requestMicrophonePermission}
          >
            Enable Microphone
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="voice-chat-container">
      {token && livekitUrl ? (
        <React.Suspense fallback={<div>Loading LiveKit components...</div>}>
          <LiveKitRoom
            serverUrl={livekitUrl}
            token={token}
            audio={true}
            video={false}
            onConnected={handleRoomEvents}
          >
            <RoomAudioRenderer />
            
            <div className="voice-chat-status">
              <div className="voice-chat-header">
                <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                  {isConnected ? 'Connected' : 'Connecting...'}
                </div>
                <div className="selector-container">
                  <LanguageSelector 
                    selectedLanguage={selectedLanguage} 
                    onChange={handleLanguageChange}
                    disabled={isSpeaking || isAssistantSpeaking}
                  />
                  <VoiceSelector
                    selectedVoice={selectedVoice}
                    onChange={handleVoiceChange}
                    disabled={isSpeaking || isAssistantSpeaking}
                    language={selectedLanguage}
                  />
                </div>
              </div>
              
              <div className="transcript-display">
                {transcript && (
                  <div className="user-transcript">
                    <strong>You:</strong> {transcript}
                  </div>
                )}
                {assistantResponse && (
                  <div className="assistant-response">
                    <strong>Assistant:</strong> {assistantResponse}
                    <FeedbackComponent />
                  </div>
                )}
              </div>
              
              <div className="voice-controls">
                <SpeakButton />
                <button 
                  className={`mode-toggle ${continuousMode ? 'continuous' : 'manual'}`}
                  onClick={() => setContinuousMode(!continuousMode)}
                  disabled={isSpeaking || isAssistantSpeaking}
                >
                  {continuousMode ? 'Continuous Mode: ON' : 'Continuous Mode: OFF'}
                </button>
                {showVoiceLimitWarning && (
                  <div className="voice-limit-warning">
                    <p>ElevenLabs custom voice limit reached. Using fallback voice. 
                    To use "Tapfuma Makina" voice, either delete other custom voices or upgrade your ElevenLabs plan.</p>
                  </div>
                )}
                {isAssistantSpeaking && (
                  <div className="speaking-indicator">
                    <div className="pulse-dot"></div>
                    <div className="pulse-dot"></div>
                    <div className="pulse-dot"></div>
                    <span>Assistant speaking...</span>
                  </div>
                )}
              </div>
            </div>
          </LiveKitRoom>
        </React.Suspense>
      ) : (
        <div className="voice-chat-loading">Connecting to voice service...</div>
      )}
    </div>
  );
};

export default VoiceChat; 