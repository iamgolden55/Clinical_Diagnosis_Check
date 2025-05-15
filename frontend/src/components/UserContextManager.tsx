import React, { useState, useEffect, useCallback } from 'react';
import './UserContextManager.css';

// Environment variables
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

interface UserContextProps {
  sessionId: string | number;
}

interface Symptom {
  name: string;
  severity: number;
}

interface Treatment {
  name: string;
  type: 'traditional' | 'modern' | 'other';
  effective: boolean | null;
}

interface MedicalHistory {
  condition: string;
  duration: string;
}

interface CulturalPreference {
  preference: string;
  importance: number;
}

interface UserContextData {
  id: number;
  session: number;
  symptoms: Record<string, Symptom>;
  symptom_durations: Record<string, string>;
  treatments_tried: Treatment[];
  medical_history: MedicalHistory[];
  cultural_preferences: Record<string, CulturalPreference>;
  language: string;
  created_at: string;
  updated_at: string;
}

const UserContextManager: React.FC<UserContextProps> = ({ sessionId }) => {
  const [contextData, setContextData] = useState<UserContextData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // UI state
  const [newSymptom, setNewSymptom] = useState<string>('');
  const [symptomSeverity, setSymptomSeverity] = useState<number>(3);
  const [symptomDuration, setSymptomDuration] = useState<string>('');
  const [newTreatment, setNewTreatment] = useState<string>('');
  const [treatmentType, setTreatmentType] = useState<'traditional' | 'modern' | 'other'>('modern');
  const [treatmentEffective, setTreatmentEffective] = useState<boolean | null>(null);
  const [newCondition, setNewCondition] = useState<string>('');
  const [conditionDuration, setConditionDuration] = useState<string>('');
  const [newPreference, setNewPreference] = useState<string>('');
  const [preferenceImportance, setPreferenceImportance] = useState<number>(3);
  const [language, setLanguage] = useState<string>('en');
  
  const fetchUserContext = useCallback(async () => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/user-context/?session_id=${sessionId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error fetching user context: ${response.statusText}`);
      }
      
      const data = await response.json();
      setContextData(data);
      
      // Update local state based on fetched data
      if (data.language) {
        setLanguage(data.language);
      }
    } catch (err: any) {
      setError(err.message || 'Error fetching user context');
      console.error('Error fetching user context:', err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);
  
  useEffect(() => {
    fetchUserContext();
  }, [fetchUserContext]);
  
  const updateContext = async (updatedData: Partial<UserContextData>) => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/user-context/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          ...updatedData
        })
      });
      
      if (!response.ok) {
        throw new Error(`Error updating user context: ${response.statusText}`);
      }
      
      const data = await response.json();
      setContextData(data);
    } catch (err: any) {
      setError(err.message || 'Error updating user context');
      console.error('Error updating user context:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handlers for adding new elements
  const handleAddSymptom = () => {
    if (!newSymptom) return;
    
    const symptoms = contextData?.symptoms || {};
    const symptomDurations = contextData?.symptom_durations || {};
    
    updateContext({
      symptoms: {
        ...symptoms,
        [newSymptom]: {
          name: newSymptom,
          severity: symptomSeverity
        }
      },
      symptom_durations: {
        ...symptomDurations,
        [newSymptom]: symptomDuration
      }
    });
    
    // Reset form
    setNewSymptom('');
    setSymptomSeverity(3);
    setSymptomDuration('');
  };
  
  const handleAddTreatment = () => {
    if (!newTreatment) return;
    
    const treatments = contextData?.treatments_tried || [];
    
    updateContext({
      treatments_tried: [
        ...treatments,
        {
          name: newTreatment,
          type: treatmentType,
          effective: treatmentEffective
        }
      ]
    });
    
    // Reset form
    setNewTreatment('');
    setTreatmentType('modern');
    setTreatmentEffective(null);
  };
  
  const handleAddMedicalHistory = () => {
    if (!newCondition) return;
    
    const history = contextData?.medical_history || [];
    
    updateContext({
      medical_history: [
        ...history,
        {
          condition: newCondition,
          duration: conditionDuration
        }
      ]
    });
    
    // Reset form
    setNewCondition('');
    setConditionDuration('');
  };
  
  const handleAddCulturalPreference = () => {
    if (!newPreference) return;
    
    const preferences = contextData?.cultural_preferences || {};
    
    updateContext({
      cultural_preferences: {
        ...preferences,
        [newPreference]: {
          preference: newPreference,
          importance: preferenceImportance
        }
      }
    });
    
    // Reset form
    setNewPreference('');
    setPreferenceImportance(3);
  };
  
  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLanguage = e.target.value;
    setLanguage(newLanguage);
    updateContext({ language: newLanguage });
  };
  
  // Handlers for removing elements
  const handleRemoveSymptom = (symptomName: string) => {
    const symptoms = { ...contextData?.symptoms } || {};
    const durations = { ...contextData?.symptom_durations } || {};
    
    delete symptoms[symptomName];
    delete durations[symptomName];
    
    updateContext({
      symptoms,
      symptom_durations: durations
    });
  };
  
  const handleRemoveTreatment = (index: number) => {
    const treatments = [...(contextData?.treatments_tried || [])];
    treatments.splice(index, 1);
    updateContext({ treatments_tried: treatments });
  };
  
  const handleRemoveMedicalHistory = (index: number) => {
    const history = [...(contextData?.medical_history || [])];
    history.splice(index, 1);
    updateContext({ medical_history: history });
  };
  
  const handleRemoveCulturalPreference = (preferenceName: string) => {
    const preferences = { ...contextData?.cultural_preferences } || {};
    delete preferences[preferenceName];
    updateContext({ cultural_preferences: preferences });
  };

  if (loading && !contextData) {
    return <div className="context-loading">Loading user context...</div>;
  }

  if (error && !contextData) {
    return <div className="context-error">Error: {error}</div>;
  }

  return (
    <div className="user-context-manager">
      <h2>Medical Context Management</h2>
      
      <div className="context-sections">
        <section className="context-section">
          <h3>Symptoms</h3>
          <div className="symptom-list">
            {Object.keys(contextData?.symptoms || {}).length === 0 ? (
              <div className="empty-list">No symptoms recorded</div>
            ) : (
              <ul>
                {Object.entries(contextData?.symptoms || {}).map(([name, symptom]) => (
                  <li key={name} className="symptom-item">
                    <div className="symptom-info">
                      <div className="symptom-name">{name}</div>
                      <div className="symptom-details">
                        <span className={`severity severity-${symptom.severity}`}>
                          Severity: {symptom.severity}/5
                        </span>
                        {contextData?.symptom_durations[name] && (
                          <span className="duration">
                            Duration: {contextData.symptom_durations[name]}
                          </span>
                        )}
                      </div>
                    </div>
                    <button 
                      className="remove-btn"
                      onClick={() => handleRemoveSymptom(name)}
                    >
                      &times;
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          <div className="add-form">
            <div className="form-row">
              <input
                type="text"
                placeholder="Symptom name"
                value={newSymptom}
                onChange={(e) => setNewSymptom(e.target.value)}
              />
              <select 
                value={symptomSeverity}
                onChange={(e) => setSymptomSeverity(parseInt(e.target.value))}
              >
                <option value={1}>Mild (1)</option>
                <option value={2}>Minor (2)</option>
                <option value={3}>Moderate (3)</option>
                <option value={4}>Severe (4)</option>
                <option value={5}>Extreme (5)</option>
              </select>
            </div>
            <div className="form-row">
              <input
                type="text"
                placeholder="Duration (e.g., 3 days, 2 weeks)"
                value={symptomDuration}
                onChange={(e) => setSymptomDuration(e.target.value)}
              />
              <button 
                className="add-btn"
                onClick={handleAddSymptom}
                disabled={!newSymptom}
              >
                Add Symptom
              </button>
            </div>
          </div>
        </section>
        
        <section className="context-section">
          <h3>Treatments Tried</h3>
          <div className="treatment-list">
            {(!contextData?.treatments_tried || contextData.treatments_tried.length === 0) ? (
              <div className="empty-list">No treatments recorded</div>
            ) : (
              <ul>
                {contextData.treatments_tried.map((treatment, index) => (
                  <li key={index} className="treatment-item">
                    <div className="treatment-info">
                      <div className="treatment-name">{treatment.name}</div>
                      <div className="treatment-details">
                        <span className={`treatment-type ${treatment.type}`}>
                          {treatment.type.charAt(0).toUpperCase() + treatment.type.slice(1)}
                        </span>
                        {treatment.effective !== null && (
                          <span className={`effectiveness ${treatment.effective ? 'effective' : 'ineffective'}`}>
                            {treatment.effective ? 'Effective' : 'Not Effective'}
                          </span>
                        )}
                      </div>
                    </div>
                    <button 
                      className="remove-btn"
                      onClick={() => handleRemoveTreatment(index)}
                    >
                      &times;
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          <div className="add-form">
            <div className="form-row">
              <input
                type="text"
                placeholder="Treatment name"
                value={newTreatment}
                onChange={(e) => setNewTreatment(e.target.value)}
              />
              <select 
                value={treatmentType}
                onChange={(e) => setTreatmentType(e.target.value as any)}
              >
                <option value="modern">Modern Medicine</option>
                <option value="traditional">Traditional Remedy</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="form-row">
              <div className="effectiveness-buttons">
                <button
                  type="button"
                  className={`effectiveness-btn ${treatmentEffective === true ? 'active' : ''}`}
                  onClick={() => setTreatmentEffective(true)}
                >
                  Effective
                </button>
                <button
                  type="button"
                  className={`effectiveness-btn ${treatmentEffective === false ? 'active' : ''}`}
                  onClick={() => setTreatmentEffective(false)}
                >
                  Not Effective
                </button>
                <button
                  type="button"
                  className={`effectiveness-btn ${treatmentEffective === null ? 'active' : ''}`}
                  onClick={() => setTreatmentEffective(null)}
                >
                  Unknown
                </button>
              </div>
              <button 
                className="add-btn"
                onClick={handleAddTreatment}
                disabled={!newTreatment}
              >
                Add Treatment
              </button>
            </div>
          </div>
        </section>
        
        <section className="context-section">
          <h3>Medical History</h3>
          <div className="history-list">
            {(!contextData?.medical_history || contextData.medical_history.length === 0) ? (
              <div className="empty-list">No medical history recorded</div>
            ) : (
              <ul>
                {contextData.medical_history.map((history, index) => (
                  <li key={index} className="history-item">
                    <div className="history-info">
                      <div className="condition-name">{history.condition}</div>
                      {history.duration && (
                        <div className="condition-duration">Duration: {history.duration}</div>
                      )}
                    </div>
                    <button 
                      className="remove-btn"
                      onClick={() => handleRemoveMedicalHistory(index)}
                    >
                      &times;
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          <div className="add-form">
            <div className="form-row">
              <input
                type="text"
                placeholder="Medical condition"
                value={newCondition}
                onChange={(e) => setNewCondition(e.target.value)}
              />
            </div>
            <div className="form-row">
              <input
                type="text"
                placeholder="Duration/When diagnosed"
                value={conditionDuration}
                onChange={(e) => setConditionDuration(e.target.value)}
              />
              <button 
                className="add-btn"
                onClick={handleAddMedicalHistory}
                disabled={!newCondition}
              >
                Add Condition
              </button>
            </div>
          </div>
        </section>
        
        <section className="context-section">
          <h3>Cultural Preferences</h3>
          <div className="preference-list">
            {Object.keys(contextData?.cultural_preferences || {}).length === 0 ? (
              <div className="empty-list">No cultural preferences recorded</div>
            ) : (
              <ul>
                {Object.entries(contextData?.cultural_preferences || {}).map(([name, preference]) => (
                  <li key={name} className="preference-item">
                    <div className="preference-info">
                      <div className="preference-name">{name}</div>
                      <div className="preference-importance">
                        Importance: {preference.importance}/5
                      </div>
                    </div>
                    <button 
                      className="remove-btn"
                      onClick={() => handleRemoveCulturalPreference(name)}
                    >
                      &times;
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          <div className="add-form">
            <div className="form-row">
              <input
                type="text"
                placeholder="Cultural preference"
                value={newPreference}
                onChange={(e) => setNewPreference(e.target.value)}
              />
              <select 
                value={preferenceImportance}
                onChange={(e) => setPreferenceImportance(parseInt(e.target.value))}
              >
                <option value={1}>Low (1)</option>
                <option value={2}>Somewhat (2)</option>
                <option value={3}>Moderate (3)</option>
                <option value={4}>High (4)</option>
                <option value={5}>Critical (5)</option>
              </select>
            </div>
            <div className="form-row">
              <button 
                className="add-btn wide-btn"
                onClick={handleAddCulturalPreference}
                disabled={!newPreference}
              >
                Add Cultural Preference
              </button>
            </div>
          </div>
        </section>
        
        <section className="context-section language-section">
          <h3>Language Preference</h3>
          <div className="language-selector">
            <select 
              value={language}
              onChange={handleLanguageChange}
            >
              <option value="en">English</option>
              <option value="pcm">Nigerian Pidgin</option>
              <option value="yo">Yoruba</option>
              <option value="ha">Hausa</option>
              <option value="ig">Igbo</option>
              <option value="sw">Swahili</option>
            </select>
          </div>
        </section>
      </div>
      
      {error && <div className="context-error-message">Error: {error}</div>}
      {loading && <div className="context-loading-indicator">Updating...</div>}
    </div>
  );
};

export default UserContextManager; 