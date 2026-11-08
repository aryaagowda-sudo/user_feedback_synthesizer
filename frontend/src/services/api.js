import axios from 'axios';
import { supabase } from './supabase';

// Vite proxy forwards /api -> http://localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach Supabase JWT auth token and user ID
apiClient.interceptors.request.use(async (config) => {
  try {
    if (supabase) {
      const { data } = await supabase.auth.getSession();
      const session = data?.session;
      if (session?.access_token) {
        config.headers['Authorization'] = `Bearer ${session.access_token}`;
        if (session.user?.id) {
          config.headers['X-User-Id'] = session.user.id;
        }
      }
    }
  } catch (err) {
    // Continue with unauthenticated / guest request
  }
  return config;
});

// Response interceptor for clear, clean error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Network error occurred';
    console.error('API Error:', message);
    return Promise.reject(new Error(message));
  }
);

export const api = {
  // Health & System Connectivity Status
  getHealth: () => apiClient.get('/'),
  getSystemStatus: () => apiClient.get('/system/status'),

  // Real-time Background Job Polling
  getAnalysisStatus: (jobId) => apiClient.get(`/analysis-status/${jobId}`),

  // Analytics Dashboard
  getAnalytics: () => apiClient.get('/analytics'),

  // Feedback Items
  getFeedback: (params = {}) => apiClient.get('/feedback', { params }),

  // Themes
  getThemes: () => apiClient.get('/themes'),

  // AI Summarization
  summarizeThemes: (themeIds = null) => apiClient.post('/summarize', { theme_ids: themeIds }),

  // AI Insights
  getInsights: () => apiClient.get('/insights'),

  // AI Feedback Copilot RAG Chatbot
  sendChat: (message, analysis_id = null) => apiClient.post('/chat', { message, analysis_id }),

  // Analysis History & Sessions
  getHistory: (userId = null) => apiClient.get('/history', { params: userId ? { user_id: userId } : {} }),
  getAnalysis: (analysisId) => apiClient.get(`/analysis/${analysisId}`),
  activateAnalysis: (analysisId) => apiClient.post(`/analysis/${analysisId}/activate`),
  deleteAnalysis: (analysisId, userId = null) => apiClient.delete(`/analysis/${analysisId}`, { params: userId ? { user_id: userId } : {} }),

  // Ingestion & AI Processing Pipeline (returns job_id immediately)
  uploadCSV: (file, userId = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (userId) {
      formData.append('user_id', userId);
    }
    return apiClient.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  analyzeRawText: (raw_text, datasetName = 'Manual Ingestion', userId = null) => 
    apiClient.post('/analyze', { raw_text, dataset_name: datasetName, user_id: userId }),

  // ==========================================================
  // ML MODEL LAB & CONTROLLED RETRAINING PIPELINE
  // ==========================================================
  uploadMLDataset: (file, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    if (options.trainRatio) formData.append('train_ratio', options.trainRatio);
    if (options.valRatio) formData.append('val_ratio', options.valRatio);
    if (options.testRatio) formData.append('test_ratio', options.testRatio);
    if (options.splitStrategy) formData.append('split_strategy', options.splitStrategy);
    return apiClient.post('/ml/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  listMLDatasets: () => apiClient.get('/ml/datasets'),

  trainModel: (params) => apiClient.post('/ml/train', params),

  getMLTrainingStatus: (jobId) => apiClient.get(`/ml/training-status/${jobId}`),

  getMLEvaluation: (modelId) => apiClient.get(`/ml/evaluation/${modelId}`),

  listMLModels: () => apiClient.get('/ml/models'),

  getCandidateEvaluation: () => apiClient.get('/ml/models/candidate-evaluation'),

  promoteCandidateModel: (candidateModelId, force = false) => 
    apiClient.post('/ml/models/promote', { candidate_model_id: candidateModelId, force }),

  rollbackModel: () => apiClient.post('/ml/models/rollback'),

  getDataDrift: () => apiClient.get('/ml/drift'),

  correctFeedbackLabel: (params) => apiClient.post('/ml/feedback/correct-label', params),

  getRetrainingStatus: () => apiClient.get('/ml/retraining-status'),

  // ==========================================================
  // HINDSIGHT AI & HISTORICAL INTELLIGENCE (BUDGET CONSCIOUS)
  // ==========================================================
  getHindsightStatus: () => apiClient.get('/hindsight/status'),

  retainHindsightMemory: (analysisId, force = false) => 
    apiClient.post(`/hindsight/retain/${analysisId}?force=${force}`),

  getHistoricalIntelligenceOverview: (analysisId = null) => 
    apiClient.get('/historical-intelligence/overview', { params: analysisId ? { analysis_id: analysisId } : {} }),

  queryHistoricalIntelligence: (analysisId, question) => 
    apiClient.post('/historical-intelligence', { analysis_id: analysisId, question }),
};
