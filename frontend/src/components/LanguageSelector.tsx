import React from 'react';
import './LanguageSelector.css';

interface LanguageSelectorProps {
  selectedLanguage: string;
  onChange: (language: string) => void;
  disabled?: boolean;
}

interface Language {
  code: string;
  name: string;
  flag?: string;
}

const languages: Language[] = [
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'en-pidgin', name: 'Nigerian Pidgin', flag: '🇳🇬' },
  { code: 'yo', name: 'Yoruba', flag: '🇳🇬' },
  { code: 'ig', name: 'Igbo', flag: '🇳🇬' },
  { code: 'ha', name: 'Hausa', flag: '🇳🇬' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
];

const LanguageSelector: React.FC<LanguageSelectorProps> = ({ 
  selectedLanguage, 
  onChange, 
  disabled = false 
}) => {
  return (
    <div className="language-selector">
      <label htmlFor="language-select">Language:</label>
      <select 
        id="language-select"
        value={selectedLanguage}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={disabled ? 'disabled' : ''}
      >
        {languages.map((language) => (
          <option key={language.code} value={language.code}>
            {language.flag} {language.name}
          </option>
        ))}
      </select>
    </div>
  );
};

export default LanguageSelector; 