import React, { useState, useEffect } from 'react';
import './ExpertReviewSystem.css';

// Environment variables
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

interface FeedbackItem {
  id: number;
  session: number;
  user_query: string;
  response_text: string;
  rating: number;
  culturally_appropriate: boolean;
  comment: string;
  created_at: string;
}

interface ExpertReview {
  id?: number;
  feedback: number;
  reviewer_name: string;
  medical_accuracy: number;
  cultural_relevance: number;
  suggested_correction: string;
  additional_notes: string;
  created_at?: string;
}

const ExpertReviewSystem: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>([]);
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [reviewerName, setReviewerName] = useState<string>('');
  const [medicalAccuracy, setMedicalAccuracy] = useState<number>(3);
  const [culturalRelevance, setCulturalRelevance] = useState<number>(3);
  const [suggestedCorrection, setSuggestedCorrection] = useState<string>('');
  const [additionalNotes, setAdditionalNotes] = useState<string>('');
  const [submitSuccess, setSubmitSuccess] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>('rating_asc'); // Default sort by lowest ratings

  useEffect(() => {
    fetchFeedbackItems();
  }, []);

  const fetchFeedbackItems = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/feedback/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error fetching feedback: ${response.statusText}`);
      }
      
      const data = await response.json();
      setFeedbackItems(data);
    } catch (err: any) {
      setError(err.message || 'Error fetching feedback data');
      console.error('Error fetching feedback:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFeedback) {
      setError('No feedback selected for review');
      return;
    }
    
    if (!reviewerName) {
      setError('Reviewer name is required');
      return;
    }
    
    const review: ExpertReview = {
      feedback: selectedFeedback.id,
      reviewer_name: reviewerName,
      medical_accuracy: medicalAccuracy,
      cultural_relevance: culturalRelevance,
      suggested_correction: suggestedCorrection,
      additional_notes: additionalNotes
    };
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/expert-review/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(review)
      });
      
      if (!response.ok) {
        throw new Error(`Error submitting review: ${response.statusText}`);
      }
      
      setSubmitSuccess(true);
      // Reset form
      setSelectedFeedback(null);
      setSuggestedCorrection('');
      setAdditionalNotes('');
      setMedicalAccuracy(3);
      setCulturalRelevance(3);
      
      // Hide success message after 3 seconds
      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
      
    } catch (err: any) {
      setError(err.message || 'Error submitting review');
      console.error('Error submitting review:', err);
    }
  };

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSortBy(e.target.value);
    
    // Sort the feedback items
    const sorted = [...feedbackItems];
    
    switch (e.target.value) {
      case 'rating_asc':
        sorted.sort((a, b) => a.rating - b.rating);
        break;
      case 'rating_desc':
        sorted.sort((a, b) => b.rating - a.rating);
        break;
      case 'date_asc':
        sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
        break;
      case 'date_desc':
        sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        break;
      case 'cultural':
        sorted.sort((a, b) => (a.culturally_appropriate === b.culturally_appropriate) ? 0 : a.culturally_appropriate ? 1 : -1);
        break;
      default:
        sorted.sort((a, b) => a.rating - b.rating);
    }
    
    setFeedbackItems(sorted);
  };

  if (loading) {
    return <div className="expert-loading">Loading feedback data...</div>;
  }

  if (error) {
    return <div className="expert-error">Error: {error}</div>;
  }

  return (
    <div className="expert-review-system">
      <h2>Expert Review System</h2>
      
      <div className="expert-content">
        <div className="feedback-list-section">
          <div className="feedback-header">
            <h3>Feedback Requiring Review</h3>
            <div className="sort-control">
              <label htmlFor="sortBy">Sort by:</label>
              <select
                id="sortBy"
                value={sortBy}
                onChange={handleSortChange}
              >
                <option value="rating_asc">Lowest Ratings First</option>
                <option value="rating_desc">Highest Ratings First</option>
                <option value="date_desc">Newest First</option>
                <option value="date_asc">Oldest First</option>
                <option value="cultural">Cultural Issues First</option>
              </select>
            </div>
          </div>
          
          {feedbackItems.length === 0 ? (
            <div className="no-feedback">No feedback items available for review.</div>
          ) : (
            <div className="feedback-list">
              {feedbackItems.map(item => (
                <div
                  key={item.id}
                  className={`feedback-item ${selectedFeedback?.id === item.id ? 'selected' : ''}`}
                  onClick={() => setSelectedFeedback(item)}
                >
                  <div className="feedback-meta">
                    <span className="feedback-date">
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                    <span className={`feedback-rating rating-${item.rating}`}>
                      {item.rating}/5
                    </span>
                    {!item.culturally_appropriate && (
                      <span className="cultural-flag">Cultural Issue</span>
                    )}
                  </div>
                  <div className="feedback-query">
                    <strong>User:</strong> {item.user_query}
                  </div>
                  <div className="feedback-response">
                    <strong>AI:</strong> {item.response_text.substring(0, 100)}...
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="review-form-section">
          <h3>Expert Review Form</h3>
          
          {submitSuccess && (
            <div className="success-message">Review submitted successfully!</div>
          )}
          
          {selectedFeedback ? (
            <>
              <div className="selected-feedback">
                <h4>Selected Conversation</h4>
                <div className="conversation-box">
                  <div className="user-message">
                    <strong>User:</strong> {selectedFeedback.user_query}
                  </div>
                  <div className="ai-response">
                    <strong>AI Response:</strong> {selectedFeedback.response_text}
                  </div>
                  <div className="feedback-details">
                    <div>
                      <strong>User Rating:</strong> {selectedFeedback.rating}/5
                    </div>
                    <div>
                      <strong>Culturally Appropriate:</strong> {selectedFeedback.culturally_appropriate ? 'Yes' : 'No'}
                    </div>
                    {selectedFeedback.comment && (
                      <div>
                        <strong>User Comment:</strong> {selectedFeedback.comment}
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              <form onSubmit={handleSubmitReview} className="review-form">
                <div className="form-group">
                  <label htmlFor="reviewerName">Reviewer Name:</label>
                  <input
                    type="text"
                    id="reviewerName"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="medicalAccuracy">Medical Accuracy (1-5):</label>
                  <div className="rating-control">
                    {[1, 2, 3, 4, 5].map(rating => (
                      <button
                        key={rating}
                        type="button"
                        className={`rating-btn ${medicalAccuracy === rating ? 'active' : ''}`}
                        onClick={() => setMedicalAccuracy(rating)}
                      >
                        {rating}
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="form-group">
                  <label htmlFor="culturalRelevance">Cultural Relevance (1-5):</label>
                  <div className="rating-control">
                    {[1, 2, 3, 4, 5].map(rating => (
                      <button
                        key={rating}
                        type="button"
                        className={`rating-btn ${culturalRelevance === rating ? 'active' : ''}`}
                        onClick={() => setCulturalRelevance(rating)}
                      >
                        {rating}
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="form-group">
                  <label htmlFor="suggestedCorrection">Suggested Correction:</label>
                  <textarea
                    id="suggestedCorrection"
                    value={suggestedCorrection}
                    onChange={(e) => setSuggestedCorrection(e.target.value)}
                    rows={5}
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="additionalNotes">Additional Notes:</label>
                  <textarea
                    id="additionalNotes"
                    value={additionalNotes}
                    onChange={(e) => setAdditionalNotes(e.target.value)}
                    rows={3}
                  />
                </div>
                
                <button type="submit" className="submit-btn">Submit Review</button>
              </form>
            </>
          ) : (
            <div className="no-selection">
              <p>Please select a feedback item from the list to review.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExpertReviewSystem; 