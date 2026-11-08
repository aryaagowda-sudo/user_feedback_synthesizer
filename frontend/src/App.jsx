import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import AnalyzeFeedback from './pages/AnalyzeFeedback';
import FeedbackExplorer from './pages/FeedbackExplorer';
import AIInsights from './pages/AIInsights';
import AICopilot from './pages/AICopilot';
import AnalysisHistory from './pages/AnalysisHistory';
import Trends from './pages/Trends';
import Settings from './pages/Settings';
import MLModelLab from './pages/MLModelLab';
import HistoricalIntelligence from './pages/HistoricalIntelligence';

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
    <AuthProvider>
      <MainLayout currentTab={currentTab} onTabChange={(tab) => setCurrentTab(tab)}>
        {renderCurrentPage()}
      </MainLayout>
    </AuthProvider>
  );
}
