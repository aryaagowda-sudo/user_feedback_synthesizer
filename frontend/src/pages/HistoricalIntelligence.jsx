import React, { useState, useEffect } from 'react';
import { 
  History, 
  BrainCircuit, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Send, 
  RefreshCw, 
  Layers, 
  ShieldCheck, 
  Database, 
  DollarSign, 
  ArrowUpRight, 
  ArrowDownRight, 
  HelpCircle,
  Flame,
  Info
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip 
} from 'recharts';
import { api } from '../services/api';

const PRESET_QUESTIONS = [
  "Which complaints have worsened over time?",
  "Which issues keep recurring across sessions?",
  "What problems have improved compared to the baseline?",
  "What new issues are emerging in recent feedback?"
];

export default function HistoricalIntelligence({ onNavigate }) {
  const [loading, setLoading] = useState(true);
  const [asking, setAsking] = useState(false);
  const [retaining, setRetaining] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState('');
  const [hindsightStatus, setHindsightStatus] = useState(null);
  const [historicalData, setHistoricalData] = useState(null);
  const [question, setQuestion] = useState(PRESET_QUESTIONS[0]);
  const [aiAnswer, setAiAnswer] = useState(null);
  const [retainMessage, setRetainMessage] = useState(null);

  // Load session history and Hindsight status
  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [histRes, statusRes] = await Promise.all([
        api.getHistory(),
        api.getHindsightStatus().catch(() => null)
      ]);

      const historyList = histRes.history || [];
      setSessions(historyList);
      if (statusRes) {
        setHindsightStatus(statusRes);
      }

      if (historyList.length > 0) {
        const defaultId = historyList[0].id || historyList[0].analysis_id;
        setSelectedAnalysisId(defaultId);
        await loadOverview(defaultId);
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error('Failed to load initial historical intelligence data:', err);
      setLoading(false);
    }
  };

  const loadOverview = async (analysisId) => {
    try {
      const res = await api.getHistoricalIntelligenceOverview(analysisId);
      setHistoricalData(res);
      setAiAnswer({
        answer: res.answer,
        hindsight_used: res.hindsight_used,
        cache_hit: res.cache_hit,
        recalled_memories: res.recalled_memories || []
      });
    } catch (err) {
      console.error('Failed to load historical overview:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const handleSessionChange = async (e) => {
    const newId = e.target.value;
    setSelectedAnalysisId(newId);
    setLoading(true);
    await loadOverview(newId);
  };

  const handleAskQuestion = async (customQ = null) => {
    const queryToAsk = customQ || question;
    if (!queryToAsk.trim() || !selectedAnalysisId) return;

    setAsking(true);
    try {
      const res = await api.queryHistoricalIntelligence(selectedAnalysisId, queryToAsk);
      setAiAnswer({
        answer: res.answer,
        hindsight_used: res.hindsight_used,
        cache_hit: res.cache_hit,
        recalled_memories: res.recalled_memories || []
      });
      if (res.usage) {
        setHindsightStatus(prev => prev ? { ...prev, usage: res.usage } : prev);
      }
    } catch (err) {
      console.error('Historical intelligence query failed:', err);
    } finally {
      setAsking(false);
    }
  };

  const handleRetainMemory = async () => {
    if (!selectedAnalysisId) return;
    setRetaining(true);
    setRetainMessage(null);
    try {
      const res = await api.retainHindsightMemory(selectedAnalysisId, false);
      setRetainMessage(res.message || 'Retention complete.');
      // Refresh status and overview
      const [statusRes] = await Promise.all([
        api.getHindsightStatus().catch(() => null),
        loadOverview(selectedAnalysisId)
      ]);
      if (statusRes) setHindsightStatus(statusRes);
    } catch (err) {
      setRetainMessage(`Retention notice: ${err.message}`);
    } finally {
      setRetaining(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-7 h-7 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin"></div>
        <p className="text-xs text-slate-400 font-mono tracking-wide">Synthesizing cross-session historical memories...</p>
      </div>
    );
  }

  const hasSufficientHistory = historicalData?.has_sufficient_history;
  const metrics = historicalData?.local_metrics || {};
  const vol = metrics.volume_metrics || {};
  const drift = metrics.sentiment_drift || {};
  const worsened = historicalData?.worsened_issues || [];
  const improving = historicalData?.improving_issues || [];
  const emerging = historicalData?.emerging_issues || [];
  const recurring = historicalData?.recurring_complaints || [];
  const themeMatrix = historicalData?.theme_matrix || [];
  const timeline = historicalData?.timeline || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header & Budget Guardrails Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 hairline-b">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">Historical Intelligence & Long-Term Memory</h1>
                <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  Hindsight AI Memory Layer
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic cross-session comparisons via Supabase with on-demand historical memory recall.
              </p>
            </div>
          </div>
        </div>

        {/* Budget Conservation & Hindsight Status Badges */}
        <div className="flex flex-wrap items-center gap-2">
          {hindsightStatus?.configured ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Hindsight Active</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>Hindsight Standby (Local Supabase Active)</span>
            </div>
          )}

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-slate-300 text-xs font-mono">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            <span>$5 Budget Protected</span>
            <span className="text-slate-500">|</span>
            <span>Calls: {hindsightStatus?.usage?.total_calls || 0}/{hindsightStatus?.usage?.session_call_budget || 50}</span>
            {hindsightStatus?.usage?.cache_hits > 0 && (
              <span className="text-indigo-400 font-semibold">({hindsightStatus.usage.cache_hits} cached)</span>
            )}
          </div>
        </div>
      </div>

      {/* Session Selector & Retain Control */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl surface-card">
        <div className="flex items-center gap-2 flex-1">
          <Layers className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-medium text-slate-300">Target Analysis:</span>
          <select
            value={selectedAnalysisId}
            onChange={handleSessionChange}
            className="flex-1 max-w-md px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
          >
            {sessions.map((s) => (
              <option key={s.id || s.analysis_id} value={s.id || s.analysis_id}>
                {s.analysis_name} ({s.total_feedback} feedback) — {String(s.created_at || '').substring(0, 10)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRetainMemory}
            disabled={retaining || !hindsightStatus?.configured}
            title={hindsightStatus?.configured ? "Retain this compact memory into Hindsight" : "Configure HINDSIGHT_API_KEY in backend/.env to retain memories"}
            className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {retaining ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <History className="w-3.5 h-3.5" />
            )}
            <span>Retain in Memory</span>
          </button>
        </div>
      </div>

      {retainMessage && (
        <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-300 flex items-center justify-between animate-in fade-in">
          <span>{retainMessage}</span>
          <button onClick={() => setRetainMessage(null)} className="text-slate-400 hover:text-white">&times;</button>
        </div>
      )}

      {/* Main Historical Content or Insufficient History Notice */}
      {!hasSufficientHistory ? (
        <div className="p-8 rounded-xl surface-card text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Clock className="w-6 h-6" />
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3 className="text-base font-semibold text-white">Not enough historical analysis data available yet</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Historical intelligence requires at least two distinct feedback analysis sessions to calculate longitudinal sentiment drift, track chronic recurring complaints, and detect emerging topics.
            </p>
          </div>
          <button
            onClick={() => onNavigate && onNavigate('analyze')}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all inline-flex items-center gap-2"
          >
            <span>Ingest Another Dataset</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <>
          {/* Historical KPI Drift Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Volume Shift */}
            <div className="p-4 rounded-xl surface-card space-y-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Volume Shift</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-white tracking-tight">{vol.current || 0}</span>
                <span className={`text-xs font-mono font-medium flex items-center gap-0.5 ${vol.change >= 0 ? 'text-indigo-400' : 'text-slate-400'}`}>
                  {vol.change >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {vol.change > 0 ? `+${vol.change}` : vol.change} ({vol.percentage_change}%)
                </span>
              </div>
              <p className="text-[11px] text-slate-500">vs. {metrics.baseline_session?.name || 'previous'}</p>
            </div>

            {/* Sentiment Drift */}
            <div className="p-4 rounded-xl surface-card space-y-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Negative Drift</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-white tracking-tight">
                  {drift.negative_drift > 0 ? `+${drift.negative_drift}%` : `${drift.negative_drift}%`}
                </span>
                <span className={`text-xs font-mono font-medium flex items-center gap-0.5 ${drift.negative_drift > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {drift.negative_drift > 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {drift.negative_drift > 0 ? 'Worsening' : 'Improving'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">Positive drift: {drift.positive_drift > 0 ? `+${drift.positive_drift}%` : `${drift.positive_drift}%`}</p>
            </div>

            {/* Recurring Complaints */}
            <div className="p-4 rounded-xl surface-card space-y-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Chronic Complaints</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-white tracking-tight">{recurring.length}</span>
                <span className="text-xs font-mono text-amber-400 flex items-center gap-0.5">
                  <Flame className="w-3.5 h-3.5" /> Multi-session
                </span>
              </div>
              <p className="text-[11px] text-slate-500">Recurring issues in both sessions</p>
            </div>

            {/* Emerging Issues */}
            <div className="p-4 rounded-xl surface-card space-y-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Emerging Topics</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-white tracking-tight">{emerging.length}</span>
                <span className="text-xs font-mono text-sky-400 flex items-center gap-0.5">
                  <Sparkles className="w-3.5 h-3.5" /> Newly detected
                </span>
              </div>
              <p className="text-[11px] text-slate-500">Not present in baseline</p>
            </div>
          </div>

          {/* Interactive Historical Copilot / Question Input */}
          <div className="p-5 rounded-xl surface-card space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Historical Intelligence Reasoning</h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                1 Recall Operation Max • Zero Repeated Billing
              </span>
            </div>

            {/* Preset Question Pills */}
            <div className="flex flex-wrap gap-2">
              {PRESET_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setQuestion(q);
                    handleAskQuestion(q);
                  }}
                  className={`px-3 py-1 rounded-full text-xs transition-all font-medium border ${
                    question === q
                      ? 'bg-indigo-600/30 text-indigo-200 border-indigo-500/50'
                      : 'bg-slate-800/60 text-slate-300 border-slate-700/60 hover:bg-slate-800'
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>

            {/* Input Bar */}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about historical patterns (e.g. Which issues have worsened?)..."
                onKeyDown={(e) => e.key === 'Enter' && handleAskQuestion()}
                className="flex-1 px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={() => handleAskQuestion()}
                disabled={asking || !question.trim()}
                className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                {asking ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>Query Memory</span>
              </button>
            </div>

            {/* AI Synthesized Answer Card */}
            {aiAnswer && (
              <div className="p-4 rounded-lg bg-slate-900/90 border border-indigo-500/30 space-y-3 animate-in fade-in">
                <div className="flex items-center justify-between hairline-b pb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-semibold text-indigo-300">Evidence-Based Historical Synthesis</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] font-mono">
                    {aiAnswer.cache_hit && (
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        ⚡ Cached (0 API Credits)
                      </span>
                    )}
                    {aiAnswer.hindsight_used && (
                      <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        🧠 1 Hindsight Recall
                      </span>
                    )}
                    {!aiAnswer.hindsight_used && !aiAnswer.cache_hit && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        📊 Pure Supabase Exact Calculation
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-line">
                  {aiAnswer.answer}
                </div>

                {/* Recalled Memory Snippets */}
                {aiAnswer.recalled_memories?.length > 0 && (
                  <div className="pt-2 border-t border-slate-800 space-y-1.5">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                      Recalled Long-Term Context from Hindsight:
                    </span>
                    <div className="space-y-1">
                      {aiAnswer.recalled_memories.map((m, i) => (
                        <div key={i} className="p-2 rounded bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-300 italic">
                          "{m.text}"
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Categorized Historical Insight Sections */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Worsened Issues Card */}
            <div className="p-4 rounded-xl surface-card space-y-3">
              <div className="flex items-center justify-between pb-2 hairline-b">
                <div className="flex items-center gap-2">
                  <TrendingDown className="w-4 h-4 text-rose-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-rose-300">Worsening Issues</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  {worsened.length} detected
                </span>
              </div>
              {worsened.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No themes experienced significant negative sentiment drift.</p>
              ) : (
                <div className="space-y-2">
                  {worsened.map((w, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-900/60 border border-rose-500/20 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">{w.theme_name}</span>
                        <span className="text-xs font-mono font-medium text-rose-400">
                          {w.negative_drift > 0 ? `+${w.negative_drift}%` : `${w.negative_drift}%`} Neg
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-snug">{w.main_complaint}</p>
                      <div className="text-[10px] font-mono text-slate-500 pt-1">
                        Mentions: {w.current_mentions} (prev: {w.previous_mentions}) • Current Neg: {w.negative_percentage}%
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Chronic Recurring Complaints Card */}
            <div className="p-4 rounded-xl surface-card space-y-3">
              <div className="flex items-center justify-between pb-2 hairline-b">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-amber-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-amber-300">Chronic Recurring Issues</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  {recurring.length} persistent
                </span>
              </div>
              {recurring.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No persistent complaints observed between current and baseline sessions.</p>
              ) : (
                <div className="space-y-2">
                  {recurring.map((r, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-900/60 border border-amber-500/20 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">{r.theme_name}</span>
                        <span className="text-xs font-mono text-amber-400">{r.average_negative_pct}% avg neg</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-snug">{r.complaint}</p>
                      <div className="text-[10px] font-mono text-slate-500 pt-1">
                        Latest: {r.current_mentions} reports • Baseline: {r.previous_mentions} reports
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Improving Issues Card */}
            <div className="p-4 rounded-xl surface-card space-y-3">
              <div className="flex items-center justify-between pb-2 hairline-b">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-300">Improving Topics</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {improving.length} resolved
                </span>
              </div>
              {improving.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No themes demonstrated at least a 5.0% negative reduction.</p>
              ) : (
                <div className="space-y-2">
                  {improving.map((imp, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-900/60 border border-emerald-500/20 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">{imp.theme_name}</span>
                        <span className="text-xs font-mono text-emerald-400">-{imp.negative_reduction}% Neg</span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 pt-1">
                        Current positive: {imp.positive_percentage}% (+{imp.positive_gain}%) • Mentions: {imp.current_mentions}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Emerging Issues Card */}
            <div className="p-4 rounded-xl surface-card space-y-3">
              <div className="flex items-center justify-between pb-2 hairline-b">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-sky-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-sky-300">Emerging New Topics</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  {emerging.length} new
                </span>
              </div>
              {emerging.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No new themes emerged; feedback remains in existing categories.</p>
              ) : (
                <div className="space-y-2">
                  {emerging.map((e, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-900/60 border border-sky-500/20 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">{e.theme_name}</span>
                        <span className="text-xs font-mono text-sky-400">{e.mentions} mentions</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-snug">{e.main_complaint}</p>
                      <div className="text-[10px] font-mono text-slate-500 pt-1">
                        Sentiment: {e.negative_percentage}% Neg • {e.positive_percentage}% Pos
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Theme Comparative Matrix Table */}
          <div className="p-5 rounded-xl surface-card space-y-3">
            <div className="flex items-center justify-between pb-2 hairline-b">
              <div>
                <h3 className="text-sm font-semibold text-white">Cross-Session Theme Comparison Matrix</h3>
                <p className="text-xs text-slate-400">Side-by-side volume and sentiment comparison against baseline session.</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                    <th className="py-2 px-3">Theme</th>
                    <th className="py-2 px-3">Current Mentions</th>
                    <th className="py-2 px-3">Previous Mentions</th>
                    <th className="py-2 px-3">Volume Delta</th>
                    <th className="py-2 px-3">Current Neg %</th>
                    <th className="py-2 px-3">Previous Neg %</th>
                    <th className="py-2 px-3">Trajectory</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {themeMatrix.map((t, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-white">{t.theme_name}</td>
                      <td className="py-2.5 px-3 font-mono">{t.current_mentions}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-400">{t.previous_mentions}</td>
                      <td className="py-2.5 px-3 font-mono">
                        <span className={t.mentions_change > 0 ? 'text-indigo-400' : (t.mentions_change < 0 ? 'text-slate-400' : 'text-slate-500')}>
                          {t.mentions_change > 0 ? `+${t.mentions_change}` : t.mentions_change}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono">{t.current_negative_pct}%</td>
                      <td className="py-2.5 px-3 font-mono text-slate-400">{t.previous_negative_pct}%</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider ${
                          t.status === 'worsened' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                          t.status === 'improved' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          t.status === 'emerging' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
                          'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}>
                          {t.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Longitudinal Sentiment Timeline Chart */}
          {timeline.length > 1 && (
            <div className="p-5 rounded-xl surface-card space-y-3">
              <div className="flex items-center justify-between pb-2 hairline-b">
                <div>
                  <h3 className="text-sm font-semibold text-white">Multi-Session Longitudinal Sentiment Velocity</h3>
                  <p className="text-xs text-slate-400">Trajectory of positive vs. negative sentiment across historical analysis runs.</p>
                </div>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="posGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                      </linearGradient>
                      <linearGradient id="negGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} unit="%" domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                      labelStyle={{ color: '#94a3b8', fontWeight: 600 }}
                    />
                    <Area type="monotone" dataKey="positive" name="Positive %" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#posGrad)" />
                    <Area type="monotone" dataKey="negative" name="Negative %" stroke="#f43f5e" strokeWidth={2} fillOpacity={1} fill="url(#negGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
