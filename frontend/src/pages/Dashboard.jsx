import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Smile, 
  Frown, 
  AlertOctagon, 
  MessageSquare, 
  ArrowUpRight, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle, 
  Zap, 
  RefreshCw,
  Clock,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  X,
  ExternalLink,
  Filter,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Tooltip as RechartsTooltip, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  BarChart, 
  Bar 
} from 'recharts';
import { api } from '../services/api';

const DEMO_DASHBOARD_DATA = {
  total_feedback: 946,
  positive_percentage: 58.2,
  neutral_percentage: 16.5,
  negative_percentage: 25.3,
  total_issues_identified: 5,
  sentiment_donut: [
    { name: 'Positive', value: 551 },
    { name: 'Neutral', value: 156 },
    { name: 'Negative', value: 239 }
  ],
  sentiment_trend: [
    { date: 'Day 1', positive: 62, neutral: 18, negative: 20 },
    { date: 'Day 2', positive: 58, neutral: 15, negative: 27 },
    { date: 'Day 3', positive: 55, neutral: 17, negative: 28 },
    { date: 'Day 4', positive: 60, neutral: 16, negative: 24 },
    { date: 'Day 5', positive: 64, neutral: 14, negative: 22 },
    { date: 'Day 6', positive: 59, neutral: 16, negative: 25 },
    { date: 'Day 7', positive: 61, neutral: 15, negative: 24 }
  ],
  top_themes: [
    { theme_name: 'Authentication & Login', mention_count: 142, positive_percentage: 12.0, negative_percentage: 82.0, neutral_percentage: 6.0, summary: 'Persistent timeout and token expiry issues on login.' },
    { theme_name: 'UI Performance & Latency', mention_count: 118, positive_percentage: 25.0, negative_percentage: 65.0, neutral_percentage: 10.0, summary: 'Dashboard and table rendering lag on large datasets.' },
    { theme_name: 'Checkout & Billing Flow', mention_count: 98, positive_percentage: 72.0, negative_percentage: 18.0, neutral_percentage: 10.0, summary: 'Seamless Stripe upgrade with high user approval.' },
    { theme_name: 'Search & Filtering', mention_count: 86, positive_percentage: 68.0, negative_percentage: 20.0, neutral_percentage: 12.0, summary: 'Accurate multi-attribute keyword search.' },
    { theme_name: 'Dark Mode Support', mention_count: 74, positive_percentage: 65.0, negative_percentage: 15.0, neutral_percentage: 20.0, is_feature_request: true, summary: 'High user request volume for system-level dark theme.' }
  ],
  top_complaints: [
    {
      theme_name: 'Authentication & Login',
      mention_count: 142,
      severity: 'Critical',
      priority: 'High',
      recommendation: 'Refresh auth tokens in background and increase session lifetime.',
      negative_percentage: 82.0,
      representative_feedback: [
        'Session expires every 10 minutes while drafting feedback reports.',
        'Login times out when connecting via SSO or Google auth.',
        'App prompts for password repeatedly after tab is backgrounded.'
      ]
    },
    {
      theme_name: 'UI Performance & Latency',
      mention_count: 118,
      severity: 'High',
      priority: 'High',
      recommendation: 'Implement virtualized scrolling for large tables.',
      negative_percentage: 65.0,
      representative_feedback: [
        'Explorer table stutters when scrolling through 500+ feedback records.',
        'Dashboard re-renders entire chart hierarchy on filter toggle.'
      ]
    }
  ],
  most_requested_features: [
    {
      theme_name: 'Dark Mode Support',
      mention_count: 74,
      priority: 'Medium',
      ai_summary: 'Users strongly prefer a high-contrast dark theme for night usage.',
      recommendation: 'Add Tailwind dark theme toggle with system preference sync.',
      representative_feedback: ['Please add a dark mode option, white interface hurts eyes at night.']
    },
    {
      theme_name: 'CSV & PDF Report Export',
      mention_count: 59,
      priority: 'Medium',
      ai_summary: 'Stakeholders require weekly executive summaries in PDF format.',
      recommendation: 'Add one-click export button generating PDF executive summary.',
      representative_feedback: ['Need to export summary charts directly to PDF for management meetings.']
    }
  ],
  priority_issues: [],
  recent_feedback: [
    { id: '1', feedback_text: 'Session expires every 10 minutes while drafting feedback reports.', sentiment: 'Negative', rating: 1, source: 'Web' },
    { id: '2', feedback_text: 'Love the new dark mode aesthetics and instant clustering!', sentiment: 'Positive', rating: 5, source: 'App' },
    { id: '3', feedback_text: 'Explorer table stutters when scrolling through 500+ feedback records.', sentiment: 'Negative', rating: 2, source: 'Web' }
  ]
};

export default function Dashboard({ onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [expandedQuotes, setExpandedQuotes] = useState({});
  const [activeComplaintModal, setActiveComplaintModal] = useState(null);

  const toggleQuoteExpansion = (id) => {
    setExpandedQuotes(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const getSeverityBadge = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'high':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    }
  };

  const handleFilterInExplorer = (complaint) => {
    if (complaint.theme_id) {
      sessionStorage.setItem('explorer_theme_filter', complaint.theme_id);
    }
    sessionStorage.setItem('explorer_sentiment_filter', 'Negative');
    if (onNavigate) {
      onNavigate('explorer');
    }
  };

  const loadAnalytics = async () => {
    try {
      setRefreshing(true);
      const res = await api.getAnalytics();
      if (!res || typeof res !== 'object' || Array.isArray(res) || !res.sentiment_donut) {
        throw new Error('Invalid analytics response payload.');
      }
      setData(res);
      setIsDemoMode(false);
      setError(null);
    } catch (err) {
      console.warn('Backend unavailable, activating demo dataset mode:', err);
      setData(DEMO_DASHBOARD_DATA);
      setIsDemoMode(true);
      setError(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-8 h-8 rounded-full border-2 border-violet-500 border-t-transparent animate-spin"></div>
        <p className="text-xs text-slate-400 font-mono tracking-wide">Synthesizing Feedback Intelligence...</p>
      </div>
    );
  }

  const {
    total_feedback = 946,
    positive_percentage = 58.2,
    neutral_percentage = 16.5,
    negative_percentage = 25.3,
    total_issues_identified = 5,
    sentiment_donut = [],
    sentiment_trend = [],
    top_themes = [],
    top_complaints = [],
    most_requested_features = [],
    priority_issues = [],
    recent_feedback = []
  } = (data && typeof data === 'object') ? data : DEMO_DASHBOARD_DATA;

  const COLORS = {
    Positive: '#10B981', // Emerald
    Neutral: '#6366F1',  // Indigo
    Negative: '#F43F5E'  // Rose
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Demo Notice Banner when backend is offline */}
      {isDemoMode && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 shadow-sm">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse shrink-0" />
            <span>
              <strong>Intelligence Preview:</strong> Displaying synthesized feedback metrics from the 946-record dataset. Connect your FastAPI backend to stream live inference data.
            </span>
          </div>
          <button
            onClick={loadAnalytics}
            className="self-start sm:self-auto px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-semibold rounded-lg border border-amber-500/30 transition-colors shrink-0"
          >
            Retry Backend
          </button>
        </div>
      )}

      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 hairline-b">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white">Feedback Intelligence Overview</h1>
            <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              Active Synthesis
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time semantic clustering and prioritized issue mitigation derived from customer feedback.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadAnalytics}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0E131F] border border-border-muted hover:border-slate-700 text-xs text-slate-300 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Sync</span>
          </button>

          <button
            onClick={() => onNavigate('analyze')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-sm transition-colors"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Upload Dataset</span>
          </button>
        </div>
      </div>

      {/* 4 Linear-style KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Feedback */}
        <div className="p-4 rounded-xl surface-card surface-card-hover">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Total Records</span>
            <div className="p-1 rounded bg-slate-800/60 text-slate-300">
              <MessageSquare className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{total_feedback}</span>
            <span className="text-[11px] text-emerald-400 font-mono font-medium flex items-center">
              <ArrowUpRight className="w-3 h-3" /> 100% Ingested
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-2 font-mono">Deduplicated customer records</p>
        </div>

        {/* Positive Sentiment */}
        <div className="p-4 rounded-xl surface-card surface-card-hover">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Positive Sentiment</span>
            <div className="p-1 rounded bg-emerald-500/10 text-emerald-400">
              <Smile className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{positive_percentage}%</span>
            <span className="text-[11px] text-slate-400 font-mono">
              {Math.round((positive_percentage / 100) * total_feedback)} users
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1 mt-2.5 overflow-hidden">
            <div className="bg-emerald-400 h-full rounded-full" style={{ width: `${positive_percentage}%` }}></div>
          </div>
        </div>

        {/* Negative Sentiment */}
        <div className="p-4 rounded-xl surface-card surface-card-hover">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Negative Sentiment</span>
            <div className="p-1 rounded bg-rose-500/10 text-rose-400">
              <Frown className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{negative_percentage}%</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
              P0 Focus
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1 mt-2.5 overflow-hidden">
            <div className="bg-rose-500 h-full rounded-full" style={{ width: `${negative_percentage}%` }}></div>
          </div>
        </div>

        {/* Priority Issues */}
        <div className="p-4 rounded-xl surface-card surface-card-hover">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Priority Issues</span>
            <div className="p-1 rounded bg-cyan-500/10 text-cyan-400">
              <AlertOctagon className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{total_issues_identified}</span>
            <span className="text-[11px] text-cyan-400 font-mono">
              across {top_themes.length} clusters
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-2 font-mono">Ranked by blocker severity</p>
        </div>
      </div>

      {/* Row 2: Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Sentiment Distribution Donut Chart (4 cols) */}
        <div className="lg:col-span-4 p-5 rounded-xl surface-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Sentiment Distribution</h2>
              <span className="text-[10px] font-mono text-slate-500">DistilBERT</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Ratio of positive, neutral, and negative customer comments</p>
          </div>

          <div className="h-52 relative flex items-center justify-center my-1">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={sentiment_donut}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {sentiment_donut.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={COLORS[entry.name] || '#6366F1'} 
                    />
                  ))}
                </Pie>
                <RechartsTooltip 
                  contentStyle={{ 
                    backgroundColor: '#0E131F', 
                    borderColor: '#1E2638', 
                    borderRadius: '8px', 
                    fontSize: '11px',
                    color: '#F8FAFC'
                  }} 
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold text-white font-mono">{total_feedback}</span>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Total</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-3 hairline-t text-center">
            {sentiment_donut.map((item) => (
              <div key={item.name} className="p-2 rounded-lg bg-white/[0.02]">
                <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: COLORS[item.name] }} />
                  <span>{item.name}</span>
                </div>
                <p className="text-xs font-bold text-white font-mono mt-0.5">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Sentiment Trend Line Chart (8 cols) */}
        <div className="lg:col-span-8 p-5 rounded-xl surface-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Feedback Sentiment Trajectory</h2>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1.5 text-emerald-400 text-[11px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Positive
                </span>
                <span className="flex items-center gap-1.5 text-rose-400 text-[11px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span> Negative
                </span>
                <span className="flex items-center gap-1.5 text-indigo-400 text-[11px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span> Neutral
                </span>
              </div>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Evolution of customer sentiment volume over ingestion dates</p>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sentiment_trend} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1E2638" opacity={0.6} />
                <XAxis 
                  dataKey="date" 
                  stroke="#475569" 
                  fontSize={10} 
                  tickLine={false}
                  tickFormatter={(val) => val.slice(5)}
                />
                <YAxis stroke="#475569" fontSize={10} tickLine={false} allowDecimals={false} />
                <RechartsTooltip 
                  contentStyle={{ 
                    backgroundColor: '#0E131F', 
                    borderColor: '#1E2638', 
                    borderRadius: '8px', 
                    fontSize: '11px',
                    color: '#F8FAFC'
                  }} 
                />
                <Line 
                  type="monotone" 
                  dataKey="positive" 
                  stroke="#10B981" 
                  strokeWidth={2} 
                  dot={{ r: 2.5, fill: '#10B981' }} 
                  activeDot={{ r: 4 }} 
                />
                <Line 
                  type="monotone" 
                  dataKey="negative" 
                  stroke="#F43F5E" 
                  strokeWidth={2} 
                  dot={{ r: 2.5, fill: '#F43F5E' }} 
                  activeDot={{ r: 4 }} 
                />
                <Line 
                  type="monotone" 
                  dataKey="neutral" 
                  stroke="#6366F1" 
                  strokeWidth={1.5} 
                  strokeDasharray="3 3"
                  dot={{ r: 2, fill: '#6366F1' }} 
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center justify-between pt-2.5 hairline-t text-[11px] text-slate-500">
            <span>Aggregated by submission timestamp</span>
            <button 
              onClick={() => onNavigate('trends')}
              className="text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1"
            >
              Temporal Velocity Details →
            </button>
          </div>
        </div>
      </div>

      {/* Row 3: Top Feedback Themes Bar Chart & Priority Issues Table */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Top Feedback Themes Bar Chart */}
        <div className="p-5 rounded-xl surface-card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Semantic Theme Volume</h2>
              <p className="text-[11px] text-slate-400 mt-0.5">Partitioned via all-MiniLM-L6-v2 embeddings</p>
            </div>
            <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/60">
              K-Means k=5
            </span>
          </div>

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={top_themes} 
                layout="vertical"
                margin={{ top: 5, right: 20, left: 25, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="2 2" stroke="#1E2638" horizontal={false} />
                <XAxis type="number" stroke="#475569" fontSize={10} tickLine={false} />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  stroke="#94A3B8" 
                  fontSize={10} 
                  tickLine={false}
                  width={140}
                  tickFormatter={(val) => val.length > 20 ? val.slice(0, 18) + '...' : val}
                />
                <RechartsTooltip 
                  contentStyle={{ 
                    backgroundColor: '#0E131F', 
                    borderColor: '#1E2638', 
                    borderRadius: '8px', 
                    fontSize: '11px' 
                  }} 
                />
                <Bar 
                  dataKey="count" 
                  radius={[0, 4, 4, 0]}
                  fill="#7C3AED"
                >
                  {top_themes.map((entry, index) => {
                    const barColor = 
                      entry.priority === 'Critical' ? '#F43F5E' : 
                      entry.priority === 'High' ? '#F59E0B' : 
                      '#7C3AED';
                    return <Cell key={`bar-${index}`} fill={barColor} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center justify-between pt-2.5 hairline-t text-[11px] text-slate-500">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Critical (P0)</span>
              <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> High (P1)</span>
              <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-violet-500"></span> Medium (P2)</span>
            </div>
            <button onClick={() => onNavigate('explorer')} className="text-violet-400 hover:text-violet-300 font-medium">
              View All →
            </button>
          </div>
        </div>

        {/* Priority Issues List */}
        <div className="p-5 rounded-xl surface-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Ranked Priority Issues</h2>
                <p className="text-[11px] text-slate-400 mt-0.5">Balanced multi-factor ranking preventing feature request inflation</p>
              </div>
              <button 
                onClick={() => onNavigate('insights')}
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
              >
                AI Insights <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-2.5">
              {priority_issues.slice(0, 4).map((issue) => {
                const isCrit = issue.level === 'Critical';
                const isHigh = issue.level === 'High';
                return (
                  <div 
                    key={issue.name} 
                    className="p-3 rounded-lg bg-[#111726] border border-border-muted hover:border-slate-700 transition-colors flex items-start gap-2.5"
                  >
                    <div className={`p-1.5 rounded shrink-0 mt-0.5 ${
                      isCrit ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                      isHigh ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-violet-500/10 text-violet-400 border border-violet-500/20'
                    }`}>
                      {isCrit ? <AlertOctagon className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-xs font-semibold text-slate-100 truncate">{issue.name}</h4>
                        <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded uppercase shrink-0 font-bold ${
                          isCrit ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20' :
                          isHigh ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20' :
                          'bg-violet-500/10 text-violet-300 border border-violet-500/20'
                        }`}>
                          P{issue.rank - 1} • {issue.level}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                        <span className="text-cyan-300 font-medium">Action: </span>
                        {issue.action}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-500 font-mono">
                        <span>{issue.mentions} reports</span>
                        <span>•</span>
                        <span className="text-rose-400">{issue.negative_pct}% negative</span>
                        <span>•</span>
                        <span>Score: {issue.score}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-2.5 hairline-t text-right">
            <span className="text-[10px] text-slate-500 font-mono">
              Formula: Severity (45) + Negative Ratio (40) + Frequency (25)
            </span>
          </div>
        </div>
      </div>

      {/* Row 4: Top Complaints & Most Requested Features */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Top User Complaints */}
        <div className="p-5 rounded-xl surface-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3.5">
              <div className="flex items-center gap-2">
                <div className="p-1 rounded bg-rose-500/10 text-rose-400">
                  <Frown className="w-3.5 h-3.5" />
                </div>
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Top User Complaints</h2>
              </div>
              <span className="text-[10px] font-mono text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                {top_complaints && top_complaints.length > 0 ? `${top_complaints.length} Root Blockers` : 'Root Blockers'}
              </span>
            </div>

            {(!top_complaints || top_complaints.length === 0) ? (
              <div className="py-10 px-4 my-2 flex flex-col items-center justify-center text-center space-y-2.5 rounded-lg border border-dashed border-border-muted bg-[#080B11]/50">
                <div className="p-2.5 rounded-full bg-slate-800/60 border border-border-muted text-slate-400">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="max-w-md space-y-1">
                  <p className="text-xs font-semibold text-slate-200">
                    No user complaints identified yet. Analyze feedback containing negative user experiences to discover issues.
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Feedback categorized under satisfactory performance or feature requests.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {top_complaints.slice(0, 3).map((comp, idx) => {
                  const compId = comp.theme_id || `complaint_${idx}`;
                  const isExpanded = !!expandedQuotes[compId];
                  const reps = comp.representative_feedback || (comp.sample ? [comp.sample] : []);

                  return (
                    <div 
                      key={compId} 
                      className="p-3.5 rounded-lg bg-[#0E131F] border border-border-muted hover:border-slate-700/80 transition-all space-y-2.5 group"
                    >
                      {/* Theme Name & Badges */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold text-slate-100 group-hover:text-rose-300 transition-colors">
                            {comp.theme_name || comp.theme}
                          </span>
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-semibold ${getSeverityBadge(comp.severity)}`}>
                            {comp.severity || 'High'} Severity
                          </span>
                          <span className="text-[10px] font-mono text-slate-300 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700">
                            Priority: {comp.priority || 'High'}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px] font-mono shrink-0">
                          <span className="text-rose-400 font-bold bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                            {comp.negative_percentage || comp.negative_pct}% Negative
                          </span>
                          <span className="text-slate-400">
                            ({comp.negative_count || comp.count}/{comp.mention_count || comp.count} reports)
                          </span>
                        </div>
                      </div>

                      {/* Complaint Summary */}
                      <p className="text-[11px] text-slate-300 leading-relaxed">
                        {comp.summary || comp.main_complaint}
                      </p>

                      {/* Representative User Quotes (Collapsible) */}
                      <div className="bg-[#080B11] p-2.5 rounded border border-border-muted/60 space-y-1.5">
                        <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                          <span className="flex items-center gap-1 text-slate-400">
                            <MessageSquare className="w-3 h-3 text-rose-400" />
                            Representative Feedback:
                          </span>
                          {reps.length > 1 && (
                            <button
                              onClick={() => toggleQuoteExpansion(compId)}
                              className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5 transition-colors"
                            >
                              {isExpanded ? 'Collapse quotes' : `+${reps.length - 1} more quote${reps.length > 2 ? 's' : ''}`}
                              {isExpanded ? <ChevronUp className="w-2.5 h-2.5" /> : <ChevronDown className="w-2.5 h-2.5" />}
                            </button>
                          )}
                        </div>

                        {/* Primary Quote */}
                        <blockquote className="text-xs text-slate-300 italic border-l-2 border-rose-500/60 pl-2 py-0.5">
                          "{reps[0] || comp.sample}"
                        </blockquote>

                        {/* Collapsible Additional Quotes */}
                        {isExpanded && reps.slice(1).map((quote, qIdx) => (
                          <blockquote key={qIdx} className="text-xs text-slate-400 italic border-l-2 border-slate-700 pl-2 py-0.5 mt-1 animate-in fade-in duration-150">
                            "{quote}"
                          </blockquote>
                        ))}
                      </div>

                      {/* Recommended Action */}
                      {comp.suggested_action && (
                        <p className="text-[11px] text-slate-400">
                          <span className="text-slate-500 font-medium">Proposal:</span> {comp.suggested_action}
                        </p>
                      )}

                      {/* Card Actions */}
                      <div className="flex items-center justify-between pt-2 hairline-t text-[11px]">
                        <button
                          onClick={() => setActiveComplaintModal(comp)}
                          className="text-slate-400 hover:text-white flex items-center gap-1 transition-colors font-medium text-xs"
                        >
                          <span>View Supporting Feedback</span>
                          <ChevronRight className="w-3 h-3 text-slate-500" />
                        </button>
                        <button
                          onClick={() => handleFilterInExplorer(comp)}
                          className="text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors font-mono font-medium text-[10px] px-2 py-0.5 rounded bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/20"
                        >
                          <span>Filter in Explorer</span>
                          <ArrowUpRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="pt-2.5 mt-3 hairline-t text-right">
            <span className="text-[10px] text-slate-500 font-mono">
              Classified by predominant negative ratio, severity impact & high-frequency reports
            </span>
          </div>
        </div>

        {/* Most Requested Features */}
        <div className="p-5 rounded-xl surface-card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1 rounded bg-violet-500/10 text-violet-400">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Most Requested Features</h2>
            </div>
            <span className="text-[10px] font-mono text-violet-400 bg-violet-500/10 px-1.5 py-0.2 rounded border border-violet-500/20">
              Ecosystem
            </span>
          </div>

          <div className="space-y-2.5">
            {most_requested_features.slice(0, 3).map((feat, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-[#111726] border border-border-muted space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-200">{feat.theme}</span>
                  <span className="text-[10px] text-violet-400 font-mono font-semibold">
                    {feat.mentions} Mentions
                  </span>
                </div>
                <blockquote className="text-xs text-slate-400 border-l border-violet-500/40 pl-2.5 italic">
                  "{feat.sample}"
                </blockquote>
                <p className="text-[11px] text-slate-300">
                  <span className="text-slate-500">Opportunity:</span> {feat.summary}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 5: Recent Feedback Records Stream */}
      <div className="p-5 rounded-xl surface-card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Recent Customer Transcripts</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Live ingested feedback with calibrated sentiment confidence</p>
          </div>
          <button 
            onClick={() => onNavigate('explorer')}
            className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
          >
            Open Explorer <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-border-muted">
          {recent_feedback.map((item) => {
            const isPos = item.sentiment === 'Positive';
            const isNeg = item.sentiment === 'Negative';
            return (
              <div key={item.id} className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-white/[0.02] px-2 rounded transition-colors">
                <div className="flex-1 min-w-0 pr-4">
                  <p className="text-xs text-slate-200 font-medium truncate">{item.feedback_text}</p>
                  <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-500 font-mono">
                    <span>{item.source || 'Web App'}</span>
                    <span>•</span>
                    <span>{item.date}</span>
                    <span>•</span>
                    <span className="text-slate-400">{item.theme_name}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 shrink-0">
                  <span className={`inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded ${
                    isPos ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    isNeg ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                    'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isPos ? 'bg-emerald-400' : isNeg ? 'bg-rose-400' : 'bg-indigo-400'}`} />
                    {item.sentiment} ({Math.round(item.confidence * 100)}%)
                  </span>

                  {item.rating && (
                    <span className="text-[10px] font-mono font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                      ★ {item.rating}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Supporting Feedback Deep-Dive Modal */}
      {activeComplaintModal && (
        <div 
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setActiveComplaintModal(null)}
        >
          <div 
            className="bg-[#0D121F] border border-slate-700/80 rounded-xl max-w-2xl w-full p-6 shadow-2xl space-y-5 text-left animate-in zoom-in-95 duration-150 relative max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-3 hairline-b pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-white">
                    {activeComplaintModal.theme_name || activeComplaintModal.theme}
                  </h3>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${getSeverityBadge(activeComplaintModal.severity)}`}>
                    {activeComplaintModal.severity || 'High'} Severity
                  </span>
                  <span className="text-[10px] font-mono text-slate-300 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                    Priority: {activeComplaintModal.priority || 'High'}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                  <span className="text-rose-400 font-semibold">{activeComplaintModal.negative_percentage || activeComplaintModal.negative_pct}% Negative Concentration</span>
                  <span>•</span>
                  <span>{activeComplaintModal.negative_count || activeComplaintModal.count} Critical Reports</span>
                  <span>•</span>
                  <span>{activeComplaintModal.mention_count || activeComplaintModal.count} Total Cluster Volume</span>
                </div>
              </div>
              <button
                onClick={() => setActiveComplaintModal(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white bg-slate-800/50 hover:bg-slate-800 border border-border-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* AI Synthesized Summary */}
            <div className="p-3.5 rounded-lg bg-[#080B11] border border-border-muted space-y-1.5">
              <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-rose-400">
                Root Friction & Customer Impact
              </span>
              <p className="text-xs text-slate-200 leading-relaxed">
                {activeComplaintModal.summary || activeComplaintModal.main_complaint}
              </p>
            </div>

            {/* Recommended Engineering Action */}
            {activeComplaintModal.suggested_action && (
              <div className="p-3.5 rounded-lg bg-violet-950/20 border border-violet-500/20 space-y-1.5">
                <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-violet-400">
                  Recommended Action & Mitigation
                </span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {activeComplaintModal.suggested_action}
                </p>
              </div>
            )}

            {/* Supporting Customer Feedback Quotes */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-rose-400" />
                  Supporting Representative Quotes
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {(activeComplaintModal.representative_feedback || []).length} quotes extracted
                </span>
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {(activeComplaintModal.representative_feedback && activeComplaintModal.representative_feedback.length > 0) ? (
                  activeComplaintModal.representative_feedback.map((quote, qIdx) => (
                    <div key={qIdx} className="p-3 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
                      <p className="text-xs text-slate-200 italic border-l-2 border-rose-500/70 pl-2.5">
                        "{quote}"
                      </p>
                      <div className="text-[10px] text-slate-500 font-mono text-right">
                        Evidence Point #{qIdx + 1}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-3 rounded-lg bg-[#080B11] border border-border-muted text-xs text-slate-400 italic">
                    "{activeComplaintModal.sample}"
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between pt-4 hairline-t">
              <button
                onClick={() => setActiveComplaintModal(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-semibold transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleFilterInExplorer(activeComplaintModal);
                  setActiveComplaintModal(null);
                }}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-sm transition-colors"
              >
                <span>Filter All in Feedback Explorer</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
