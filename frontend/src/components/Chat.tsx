import React, { useState, useEffect, useRef } from 'react';
import './Chat.css';

// Add TypeScript declarations for SpeechRecognition APIs
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionResultList {
  readonly length: number;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionAlternative {
  readonly transcript: string;
  readonly confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onend: () => void;
}

// Add window interfaces
declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognition;
    webkitSpeechRecognition?: new () => SpeechRecognition;
  }
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  entities?: Record<string, string[]>;
  emotion?: {
    emotion: string;
    confidence: number;
  };
}

interface SummaryData {
  summary: string;
  extracted_entities: Record<string, string[]>;
  emotional_analysis: {
    dominant_emotion: string;
    emotion_breakdown: Record<string, number>;
  };
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [showSummary, setShowSummary] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Initialize speech recognition
  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      
      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0])
          .map(result => result.transcript)
          .join('');
        
        setInput(transcript);
      };
      
      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);
  
  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
      setInput('');
    }
  };
  
  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);

    const payload: any = { message: input };
    if (sessionId) payload.session_id = sessionId;

    setInput('');
    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errorData = await response.text();
        console.error('API error:', response.status, errorData);
        throw new Error(`Failed to fetch: ${response.status}`);
      }
      const data = await response.json();
      
      // Update last user message with entity and emotion data
      if (data.entities || data.emotion) {
        setMessages(prev => {
          const updated = [...prev];
          if (updated.length > 0) {
            const lastUserMsg = updated[updated.length - 1];
            if (lastUserMsg.role === 'user') {
              lastUserMsg.entities = data.entities;
              lastUserMsg.emotion = data.emotion;
            }
          }
          return updated;
        });
      }
      
      const assistantMsg: Message = { role: 'assistant', content: data.reply };
      setMessages(prev => [...prev, assistantMsg]);
      if (data.session_id) setSessionId(data.session_id);
      
      // Speak the assistant's response
      speakText(data.reply);
    } catch (err) {
      console.error(err);
      const errorMsg: Message = { role: 'assistant', content: 'Error: could not get response.' };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };
  
  const generateSummary = async () => {
    if (!sessionId) return;
    
    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/summary/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      
      if (!response.ok) {
        const errorData = await response.text();
        console.error('Summary API error:', response.status, errorData);
        throw new Error(`Failed to generate summary: ${response.status}`);
      }
      
      const data = await response.json();
      setSummaryData({
        summary: data.summary,
        extracted_entities: data.extracted_entities || {},
        emotional_analysis: data.emotional_analysis || {
          dominant_emotion: 'unknown',
          emotion_breakdown: {}
        }
      });
      setShowSummary(true);
    } catch (err) {
      console.error(err);
      alert('Error generating summary. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Helper to render medical entities
  const renderEntities = (entities: Record<string, string[]>) => {
    return Object.entries(entities).map(([type, terms]) => (
      <div key={type} className="entity-item">
        <span className="entity-type">{type}:</span> {terms.join(', ')}
      </div>
    ));
  };

  // Helper to render emotion data
  const renderEmotion = (emotion: { emotion: string; confidence: number }) => {
    // Only show emotions with meaningful confidence levels
    if (emotion.emotion === "unknown" || emotion.confidence < 0.5) {
      return null; // Don't display anything for unknown emotions or low confidence
    }
    
    return (
      <div className="emotion-indicator">
        <span className="emotion-label">Detected emotion:</span>
        <span className={`emotion-value ${emotion.emotion}`}>
          {emotion.emotion} ({(emotion.confidence * 100).toFixed(0)}%)
        </span>
      </div>
    );
  };

  return (
    <div className="chat-container">
      {!showSummary ? (
        <>
          <div className="message-list">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-content">{msg.content}</div>
                {msg.role === 'user' && msg.entities && Object.keys(msg.entities).length > 0 && (
                  <div className="message-metadata">
                    <div className="entities-container">
                      {renderEntities(msg.entities)}
                    </div>
                  </div>
                )}
                {msg.role === 'user' && msg.emotion && msg.emotion.emotion !== 'unknown' && msg.emotion.confidence >= 0.5 && (
                  <div className="message-metadata">
                    {renderEmotion(msg.emotion)}
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          <div className="chat-controls">
            <div className="chat-input-container">
              <input
                type="text"
                className="chat-input"
                placeholder="Type your message..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading || isListening}
              />
              <button 
                onClick={toggleListening} 
                className={`mic-btn ${isListening ? 'listening' : ''}`} 
                disabled={loading}
              >
                🎤
              </button>
              <button onClick={sendMessage} className="send-btn" disabled={loading || !input.trim()}>
                {loading ? '...' : 'Send'}
              </button>
            </div>
            {messages.length > 1 && (
              <button onClick={generateSummary} className="summary-btn" disabled={loading}>
                Generate Summary for Doctor
              </button>
            )}
          </div>
        </>
      ) : (
        <div className="summary-container">
          <h2>Patient Consultation Summary</h2>
          <div className="summary-content">
            {summaryData?.summary}
          </div>
          
          {summaryData && Object.keys(summaryData.extracted_entities).length > 0 && (
            <div className="summary-entities">
              <h3>Detected Medical Entities</h3>
              <div className="entities-list">
                {renderEntities(summaryData.extracted_entities)}
              </div>
            </div>
          )}
          
          {summaryData?.emotional_analysis.dominant_emotion !== 'unknown' && (
            <div className="summary-emotions">
              <h3>Patient Emotional Analysis</h3>
              <div className="emotion-dominant">
                <strong>Dominant emotion:</strong> {summaryData.emotional_analysis.dominant_emotion}
              </div>
              <div className="emotion-breakdown">
                {Object.entries(summaryData.emotional_analysis.emotion_breakdown).map(([emotion, percentage]) => (
                  <div key={emotion} className="emotion-breakdown-item">
                    <span className={`emotion-name ${emotion}`}>{emotion}</span>
                    <div className="emotion-bar-container">
                      <div className="emotion-bar" style={{ width: `${percentage}%` }}></div>
                      <span className="emotion-percentage">{percentage.toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <button onClick={() => setShowSummary(false)} className="back-btn">
            Back to Chat
          </button>
        </div>
      )}
    </div>
  );
};

export default Chat; 