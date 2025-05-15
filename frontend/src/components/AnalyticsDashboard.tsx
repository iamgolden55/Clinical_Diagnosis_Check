import React, { useState, useEffect } from 'react';
import './AnalyticsDashboard.css';

// Chart.js for visualizations
import { 
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

// Environment variables
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

const AnalyticsDashboard: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [dateRange, setDateRange] = useState<{from: string, to: string}>({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 30 days ago
    to: new Date().toISOString().split('T')[0] // today
  });

  useEffect(() => {
    fetchAnalytics();
  }, [dateRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/analytics/dashboard/?from_date=${dateRange.from}&to_date=${dateRange.to}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        }
      );
      
      if (!response.ok) {
        throw new Error(`Error fetching analytics: ${response.statusText}`);
      }
      
      const data = await response.json();
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || 'Error fetching analytics data');
      console.error('Error fetching analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle date range changes
  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setDateRange(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Generate chart data
  const getRatingChartData = () => {
    if (!analytics || !analytics.time_series || !analytics.time_series.avg_rating) {
      return {
        labels: [],
        datasets: [{
          label: 'Average Rating',
          data: [],
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
        }]
      };
    }
    
    const data = analytics.time_series.avg_rating;
    return {
      labels: data.map((item: any) => item.date),
      datasets: [{
        label: 'Average Rating',
        data: data.map((item: any) => item.value),
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.1
      }]
    };
  };

  const getCulturalScoreChartData = () => {
    if (!analytics || !analytics.time_series || !analytics.time_series.cultural_score) {
      return {
        labels: [],
        datasets: [{
          label: 'Cultural Appropriateness Score',
          data: [],
          borderColor: 'rgba(153, 102, 255, 1)',
          backgroundColor: 'rgba(153, 102, 255, 0.2)',
        }]
      };
    }
    
    const data = analytics.time_series.cultural_score;
    return {
      labels: data.map((item: any) => item.date),
      datasets: [{
        label: 'Cultural Appropriateness Score',
        data: data.map((item: any) => item.value),
        borderColor: 'rgba(153, 102, 255, 1)',
        backgroundColor: 'rgba(153, 102, 255, 0.2)',
        tension: 0.1
      }]
    };
  };

  const getFeedbackCountChartData = () => {
    if (!analytics || !analytics.time_series || !analytics.time_series.feedback_count) {
      return {
        labels: [],
        datasets: [{
          label: 'Feedback Count',
          data: [],
          backgroundColor: 'rgba(255, 159, 64, 0.7)',
        }]
      };
    }
    
    const data = analytics.time_series.feedback_count;
    return {
      labels: data.map((item: any) => item.date),
      datasets: [{
        label: 'Feedback Count',
        data: data.map((item: any) => item.value),
        backgroundColor: 'rgba(255, 159, 64, 0.7)',
      }]
    };
  };

  if (loading) {
    return <div className="analytics-loading">Loading analytics data...</div>;
  }

  if (error) {
    return <div className="analytics-error">Error: {error}</div>;
  }

  return (
    <div className="analytics-dashboard">
      <h2>Analytics Dashboard</h2>
      
      <div className="date-range-selector">
        <div className="date-input">
          <label htmlFor="from">From:</label>
          <input
            type="date"
            id="from"
            name="from"
            value={dateRange.from}
            onChange={handleDateChange}
          />
        </div>
        <div className="date-input">
          <label htmlFor="to">To:</label>
          <input
            type="date"
            id="to"
            name="to"
            value={dateRange.to}
            onChange={handleDateChange}
          />
        </div>
        <button onClick={fetchAnalytics} className="refresh-btn">Refresh</button>
      </div>
      
      {analytics && (
        <>
          <div className="metrics-summary">
            <div className="metric-card">
              <h3>Average Rating</h3>
              <div className="metric-value">{analytics.overall.avg_rating.toFixed(1)}</div>
              <div className="metric-icon">⭐</div>
            </div>
            
            <div className="metric-card">
              <h3>Cultural Score</h3>
              <div className="metric-value">{analytics.overall.cultural_score.toFixed(1)}%</div>
              <div className="metric-icon">🌍</div>
            </div>
            
            <div className="metric-card">
              <h3>Total Feedback</h3>
              <div className="metric-value">{analytics.overall.feedback_count}</div>
              <div className="metric-icon">📝</div>
            </div>
          </div>
          
          <div className="charts-container">
            <div className="chart-wrapper">
              <h3>Rating Trends</h3>
              <Line data={getRatingChartData()} options={{ 
                responsive: true,
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                    ticks: { stepSize: 1 }
                  }
                }
              }} />
            </div>
            
            <div className="chart-wrapper">
              <h3>Cultural Appropriateness</h3>
              <Line data={getCulturalScoreChartData()} options={{
                responsive: true,
                scales: {
                  y: {
                    min: 0,
                    max: 100,
                    ticks: { stepSize: 20 }
                  }
                }
              }} />
            </div>
            
            <div className="chart-wrapper">
              <h3>Feedback Volume</h3>
              <Bar data={getFeedbackCountChartData()} options={{
                responsive: true,
              }} />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AnalyticsDashboard; 