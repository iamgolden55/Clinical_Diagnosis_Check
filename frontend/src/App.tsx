import React, { useState } from 'react';
import './App.css';
import Chat from './components/Chat';
import VoiceChat from './components/VoiceChat';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import ExpertReviewSystem from './components/ExpertReviewSystem';
import UserContextManager from './components/UserContextManager';
import DataPipelineManager from './components/DataPipelineManager';

// Custom healthcare-focused welcome message
const HEALTHCARE_WELCOME_MESSAGE = "Welcome to EleraAI Healthcare Assistant. I'm here to help with medical information, symptom assessment, and healthcare advice. Please note I'm an AI assistant and not a replacement for professional medical care. How can I assist with your health concerns today?";

function App() {
  const [chatMode, setChatMode] = useState<'text' | 'voice'>('text');
  const [userName, setUserName] = useState('User');
  const [conversationId, setConversationId] = useState<string>(
    `session-${Math.random().toString(36).substring(2, 10)}`
  );
  const [activeTab, setActiveTab] = useState<'chat' | 'analytics' | 'expert-review' | 'context' | 'pipeline'>('chat');

  const toggleChatMode = () => {
    setChatMode(prevMode => prevMode === 'text' ? 'voice' : 'text');
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>EleraAI Healthcare Assistant</h1>
        <nav className="main-navigation">
          <button 
            className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat
          </button>
          <button 
            className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            Analytics
          </button>
          <button 
            className={`nav-tab ${activeTab === 'expert-review' ? 'active' : ''}`}
            onClick={() => setActiveTab('expert-review')}
          >
            Expert Review
          </button>
          <button 
            className={`nav-tab ${activeTab === 'context' ? 'active' : ''}`}
            onClick={() => setActiveTab('context')}
          >
            Medical Context
          </button>
          <button 
            className={`nav-tab ${activeTab === 'pipeline' ? 'active' : ''}`}
            onClick={() => setActiveTab('pipeline')}
          >
            Data Pipeline
          </button>
        </nav>
      </header>
      
      <main className="App-main">
        {activeTab === 'chat' && (
          <div className="chat-container">
            <div className="mode-toggle">
              <button 
                className={`mode-button ${chatMode === 'text' ? 'active' : ''}`} 
                onClick={() => setChatMode('text')}
              >
                Text Mode
              </button>
              <button 
                className={`mode-button ${chatMode === 'voice' ? 'active' : ''}`} 
                onClick={() => setChatMode('voice')}
              >
                Voice Mode
              </button>
            </div>
            
            {chatMode === 'text' ? (
              <Chat />
            ) : (
              <VoiceChat 
                conversationId={conversationId}
                userName={userName}
                welcomeMessage={HEALTHCARE_WELCOME_MESSAGE}
                onTranscriptUpdate={(transcript) => {
                  console.log('Transcript updated:', transcript);
                }}
              />
            )}
          </div>
        )}
        
        {activeTab === 'analytics' && (
          <AnalyticsDashboard />
        )}
        
        {activeTab === 'expert-review' && (
          <ExpertReviewSystem />
        )}
        
        {activeTab === 'context' && (
          <UserContextManager sessionId={conversationId} />
        )}
        
        {activeTab === 'pipeline' && (
          <DataPipelineManager />
        )}
      </main>
    </div>
  );
}

export default App;
