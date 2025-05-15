import React, { useState, useEffect } from 'react';
import './VoiceSelector.css';

interface VoiceSelectorProps {
  selectedVoice: string;
  onChange: (voiceId: string) => void;
  disabled?: boolean;
  language?: string;
}

interface Voice {
  id: string;
  name: string;
  description: string;
}

// Map of default voice IDs by language
const DEFAULT_VOICES: {[key: string]: Voice} = {
  "en": { id: "EXAVITQu4vr4xnSDxMaL", name: "Rachel", description: "Clear English voice" },
  "en-pidgin": { id: "jsCqWAovK2LkecY7zXl4", name: "African", description: "Perfect for Nigerian Pidgin" },
  "yo": { id: "jsCqWAovK2LkecY7zXl4", name: "African", description: "Yoruba approximation" },
  "ig": { id: "jsCqWAovK2LkecY7zXl4", name: "African", description: "Igbo approximation" },
  "ha": { id: "jsCqWAovK2LkecY7zXl4", name: "African", description: "Hausa approximation" },
  "fr": { id: "t0jbNlBVZ17f02VDIeMI", name: "Rémi", description: "French voice" },
  "es": { id: "ErXwobaYiN019PkySvjV", name: "Antoni", description: "Spanish voice" },
};

// Popular ElevenLabs voices
const POPULAR_VOICES: Voice[] = [
  { id: "CJsvtXkl6ObQJrCz44le", name: "Tapfuma Makina", description: "Nigerian accent (Premium)" },
  { id: "jsCqWAovK2LkecY7zXl4", name: "African", description: "Warm Nigerian accent" },
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Rachel", description: "Clear English female voice" },
  { id: "TxGEqnHWrfWFTfGW9XjX", name: "Josh", description: "Natural male voice" },
  { id: "ThT5KcBeYPX3keUQqHPh", name: "Bella", description: "Warm female voice" },
  { id: "t0jbNlBVZ17f02VDIeMI", name: "Rémi", description: "French male voice" },
  { id: "ErXwobaYiN019PkySvjV", name: "Antoni", description: "Spanish male voice" },
  { id: "c4YYXKgQZYTxcBUj9baM", name: "Gigi", description: "American female voice" },
  { id: "SOYHLrjzK2X1ezoPC6cr", name: "Thomas", description: "British male voice" },
];

const VoiceSelector: React.FC<VoiceSelectorProps> = ({ 
  selectedVoice, 
  onChange, 
  disabled = false,
  language = 'en'
}) => {
  // Set initial voice based on language
  useEffect(() => {
    if (!selectedVoice && language && DEFAULT_VOICES[language]) {
      onChange(DEFAULT_VOICES[language].id);
    }
  }, [language, selectedVoice, onChange]);

  return (
    <div className="voice-selector">
      <label htmlFor="voice-select">AI Voice:</label>
      <select 
        id="voice-select"
        value={selectedVoice || (DEFAULT_VOICES[language]?.id || '')}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={disabled ? 'disabled' : ''}
      >
        {language && DEFAULT_VOICES[language] && (
          <option value={DEFAULT_VOICES[language].id}>
            {DEFAULT_VOICES[language].name} (Recommended for {language})
          </option>
        )}
        
        <optgroup label="Popular Voices">
          {POPULAR_VOICES.map((voice) => (
            voice.id !== (DEFAULT_VOICES[language]?.id || '') && (
              <option key={voice.id} value={voice.id}>
                {voice.name} - {voice.description}
              </option>
            )
          ))}
        </optgroup>
      </select>
    </div>
  );
};

export default VoiceSelector; 