import React, { useState, Suspense, lazy } from 'react';
import { AuthProvider } from './context/AuthContext';
import MainLayout from './layouts/MainLayout';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('FeedbackIQ ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold text-xl">
            !
          </div>
          <h2 className="text-lg font-bold text-white">Application Notice</h2>
          <p className="text-xs text-slate-400 max-w-md font-mono bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-lg"
          >
            Reload View
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// Route-based code splitting with React.lazy
const Dashboard = lazy(() => import('./pages/Dashboard'));
const AnalyzeFeedback = lazy(() => import('./pages/AnalyzeFeedback'));
const FeedbackExplorer = lazy(() => import('./pages/FeedbackExplorer'));
const AIInsights = lazy(() => import('./pages/AIInsights'));
const AICopilot = lazy(() => import('./pages/AICopilot'));
const AnalysisHistory = lazy(() => import('./pages/AnalysisHistory'));
const Trends = lazy(() => import('./pages/Trends'));
const Settings = lazy(() => import('./pages/Settings'));
const MLModelLab = lazy(() => import('./pages/MLModelLab'));
const HistoricalIntelligence = lazy(() => import('./pages/HistoricalIntelligence'));

function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
      <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
      <p className="text-sm text-slate-400 font-medium animate-pulse">Loading view...</p>
    </div>
  );
}

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');

  const renderCurrentPage = () => {
    switch (currentTab) {
      case 'dashboard':
        return <Dashboard onNavigate={(tab) => setCurrentTab(tab)} />;
      case 'analyze':
        return <AnalyzeFeedback onNavigate={(tab) => setCurrentTab(tab)} />;
      case 'explorer':
        return <FeedbackExplorer />;
      case 'insights':
        return <AIInsights onNavigate={(tab) => setCurrentTab(tab)} />;
      case 'copilot':
        return <AICopilot />;
      case 'historical':
        return <HistoricalIntelligence onNavigate={(tab) => setCurrentTab(tab)} />;
      case 'history':
        return <AnalysisHistory onNavigate={(tab) => setCurrentTab(tab)} />;
      case 'trends':
        return <Trends />;
      case 'ml-lab':
        return <MLModelLab onNavigate={(tab) => setCurrentTab(tab)} />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard onNavigate={(tab) => setCurrentTab(tab)} />;
    }
  };

  return (
    <ErrorBoundary>
      <AuthProvider>
        <MainLayout currentTab={currentTab} onTabChange={(tab) => setCurrentTab(tab)}>
          <ErrorBoundary>
            <Suspense fallback={<PageLoader />}>
              {renderCurrentPage()}
            </Suspense>
          </ErrorBoundary>
        </MainLayout>
      </AuthProvider>
    </ErrorBoundary>
  );
}
