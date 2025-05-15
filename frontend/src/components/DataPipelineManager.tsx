import React, { useState, useEffect } from 'react';
import './DataPipelineManager.css';

// Environment variables
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

interface Dataset {
  filename: string;
  size: number;
  created: string;
  path: string;
}

interface Metric {
  id: number;
  type: string;
  date: string;
  value: number;
  text_value: string | null;
}

interface PipelineStats {
  datasets: Dataset[];
  latest_metrics: Metric[];
}

const DataPipelineManager: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [operation, setOperation] = useState<'update_metrics' | 'generate_training'>('update_metrics');
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');
  const [minRating, setMinRating] = useState<number>(4);
  const [operationResult, setOperationResult] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchPipelineStats();
  }, []);

  const fetchPipelineStats = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/data-pipeline/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error fetching pipeline stats: ${response.statusText}`);
      }
      
      const data = await response.json();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Error fetching pipeline statistics');
      console.error('Error fetching pipeline stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const handleRunOperation = async () => {
    setIsProcessing(true);
    setError(null);
    setOperationResult(null);
    setSuccessMessage(null);
    
    const payload: any = {
      operation: operation
    };
    
    if (fromDate) {
      payload.from_date = fromDate;
    }
    
    if (toDate) {
      payload.to_date = toDate;
    }
    
    if (operation === 'generate_training') {
      payload.min_rating = minRating;
    }
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/data-pipeline/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        throw new Error(`Error running operation: ${response.statusText}`);
      }
      
      const result = await response.json();
      setOperationResult(result);
      
      // Show success message
      if (operation === 'update_metrics') {
        setSuccessMessage(`Successfully updated metrics. Created: ${result.metrics_created}, Updated: ${result.metrics_updated}`);
      } else {
        setSuccessMessage(`Successfully generated training data with ${result.total_samples} samples.`);
      }
      
      // Refresh pipeline stats
      fetchPipelineStats();
    } catch (err: any) {
      setError(err.message || 'Error running operation');
      console.error('Error running operation:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const getMetricTypeDisplay = (type: string): string => {
    const typeMap: Record<string, string> = {
      'avg_rating': 'Average Rating',
      'cultural_score': 'Cultural Appropriateness Score',
      'feedback_count': 'Feedback Count',
      'common_issue': 'Common Issues',
      'medical_accuracy': 'Medical Accuracy',
      'cultural_relevance': 'Cultural Relevance',
    };
    
    return typeMap[type] || type;
  };

  if (loading && !stats) {
    return <div className="pipeline-loading">Loading pipeline data...</div>;
  }

  if (error && !stats) {
    return <div className="pipeline-error">Error: {error}</div>;
  }

  return (
    <div className="data-pipeline-manager">
      <h2>Data Pipeline Manager</h2>
      
      <div className="pipeline-sections">
        <section className="pipeline-section">
          <h3>Run Pipeline Operations</h3>
          
          <div className="operation-form">
            <div className="form-group">
              <label htmlFor="operation">Operation:</label>
              <select
                id="operation"
                value={operation}
                onChange={(e) => setOperation(e.target.value as any)}
              >
                <option value="update_metrics">Update Analytics Metrics</option>
                <option value="generate_training">Generate Training Data</option>
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="fromDate">From Date (optional):</label>
              <input
                type="date"
                id="fromDate"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="toDate">To Date (optional):</label>
              <input
                type="date"
                id="toDate"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
              />
            </div>
            
            {operation === 'generate_training' && (
              <div className="form-group">
                <label htmlFor="minRating">Minimum Rating:</label>
                <select
                  id="minRating"
                  value={minRating}
                  onChange={(e) => setMinRating(parseInt(e.target.value))}
                >
                  <option value={1}>1 - Include All Ratings</option>
                  <option value={2}>2 - Exclude Very Poor</option>
                  <option value={3}>3 - Average and Above</option>
                  <option value={4}>4 - Good and Above</option>
                  <option value={5}>5 - Only Excellent</option>
                </select>
              </div>
            )}
            
            <button 
              className="run-btn"
              onClick={handleRunOperation}
              disabled={isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Run Operation'}
            </button>
            
            {error && <div className="pipeline-error-message">Error: {error}</div>}
            {successMessage && <div className="pipeline-success-message">{successMessage}</div>}
          </div>
          
          {operationResult && (
            <div className="operation-result">
              <h4>Operation Result</h4>
              <pre>{JSON.stringify(operationResult, null, 2)}</pre>
            </div>
          )}
        </section>
        
        <section className="pipeline-section">
          <h3>Available Training Datasets</h3>
          
          {stats && stats.datasets.length === 0 ? (
            <div className="no-datasets">No training datasets available.</div>
          ) : (
            <div className="datasets-list">
              <table>
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Size</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.datasets.map((dataset, index) => (
                    <tr key={index}>
                      <td>{dataset.filename}</td>
                      <td>{formatBytes(dataset.size)}</td>
                      <td>{formatDate(dataset.created)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        
        <section className="pipeline-section">
          <h3>Latest Analytics Metrics</h3>
          
          {stats && stats.latest_metrics.length === 0 ? (
            <div className="no-metrics">No metrics available.</div>
          ) : (
            <div className="metrics-list">
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Date</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.latest_metrics.map((metric) => (
                    <tr key={metric.id}>
                      <td>{getMetricTypeDisplay(metric.type)}</td>
                      <td>{formatDate(metric.date)}</td>
                      <td>
                        {metric.type === 'common_issue' ? 
                          metric.text_value : 
                          metric.type.includes('score') ? 
                            `${metric.value.toFixed(2)}%` : 
                            metric.value.toFixed(2)
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
      
      <div className="refresh-section">
        <button 
          className="refresh-btn"
          onClick={fetchPipelineStats}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh Stats'}
        </button>
      </div>
    </div>
  );
};

export default DataPipelineManager; 