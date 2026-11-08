import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Bot, 
  AlertTriangle, 
  CheckCircle2, 
  Flame, 
  Lightbulb, 
  TrendingUp, 
  Layers,
  Quote,
  RefreshCw,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  BarChart3
} from 'lucide-react';
import { api } from '../services/api';

export default function AIInsights({ onNavigate }) {
  const [insights, setInsights] = useState(null);
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [summarizing, setSummarizing] = useState(false);
  const [selectedThemeId, setSelectedThemeId] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [insightsRes, themesRes] = await Promise.all([
        api.getInsights(),
        api.getThemes()
      ]);
      setInsights(insightsRes);
      setThemes(themesRes.themes || []);
      if (themesRes.themes?.length > 0) {
        setSelectedThemeId(themesRes.themes[0].id);
      }
    } catch (err) {
      console.error('Failed to load insights & themes:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRegenerateSummaries = async () => {
    setSummarizing(true);
    try {
      const res = await api.summarizeThemes();
      if (res.themes) {
        setThemes(res.themes);
      }
      await fetchData();
    } catch (err) {
      console.error('Failed to regenerate summaries:', err);
    } finally {
      setSummarizing(false);
    }
  };

  const getPriorityBadgeClass = (priority) => {
    switch ((priority || '').toLowerCase()) {
      case 'critical':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/25';
      case 'high':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/25';
      case 'medium':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/25';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/25';
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 hairline-b">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white">AI Feedback Intelligence & Theme Summaries</h1>
            <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">
              Evidence-Based Synthesis
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Automated LLM clustering summaries, friction prioritization, and verified customer evidence.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleRegenerateSummaries}
            disabled={summarizing || loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0E131F] border border-border-muted hover:border-slate-700 text-xs text-slate-300 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${summarizing ? 'animate-spin' : ''}`} />
            <span>{summarizing ? 'Summarizing...' : 'Re-summarize Themes'}</span>
          </button>

          <button
            onClick={() => onNavigate && onNavigate('copilot')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-sm transition-colors"
          >
            <Bot className="w-3.5 h-3.5" />
            <span>Open AI Copilot</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 rounded-xl surface-card text-center">
          <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-mono">Synthesizing evidence-based intelligence across clusters...</p>
        </div>
      ) : (
        <>
          {/* Executive Summary Banner */}
          {insights && (
            <div className="p-4 rounded-xl bg-gradient-to-r from-violet-950/20 via-[#0E131F] to-[#0E131F] border border-violet-500/20 space-y-1.5">
              <div className="flex items-center gap-1.5 text-violet-300 font-bold text-[11px] uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>Executive Synthesis & Root Problem</span>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed font-sans">
                {insights.summary}
              </p>
            </div>
          )}

          {/* Section: Clustered AI Theme Summaries & Recommendations */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-violet-400" />
                <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                  Clustered Theme Summaries ({themes.length} Themes)
                </h2>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                Ranked by Operational Urgency
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {themes.map((theme, idx) => {
                const name = theme.theme_name || theme.name;
                const prio = theme.priority || theme.priority_level || 'Medium';
                const mentions = theme.mention_count || 0;
                const posPct = theme.positive_percentage || theme.sentiment_distribution?.positive_pct || 0;
                const negPct = theme.negative_percentage || theme.sentiment_distribution?.negative_pct || 0;
                const neuPct = theme.neutral_percentage || theme.sentiment_distribution?.neutral_pct || 0;
                const complaint = theme.main_complaint || "Usability friction reported.";
                const observations = theme.key_observations || [];
                const summary = theme.ai_summary || theme.summary || "No summary generated.";
                const rec = theme.recommendation || theme.suggested_action || "Investigate root cause.";
                const reps = theme.representative_feedback || theme.representative_comments || [];

                return (
                  <div
                    key={theme.id || idx}
                    className="p-5 rounded-xl surface-card space-y-4 border border-border-muted hover:border-violet-500/40 transition-all flex flex-col justify-between"
                  >
                    <div className="space-y-3">
                      {/* Theme Top Row: Title, Priority, Mentions */}
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-bold text-white tracking-tight">{name}</h3>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${getPriorityBadgeClass(prio)}`}>
                              {prio} Priority
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                            Rank #{theme.priority_rank || idx + 1} • {mentions} Mentions • Severity: {theme.severity || 'Medium'}
                          </p>
                        </div>

                        {/* Sentiment Pill Bar */}
                        <div className="text-right shrink-0">
                          <div className="flex items-center gap-1 text-[10px] font-mono">
                            <span className="text-rose-400 font-semibold">{negPct}% Neg</span>
                            <span className="text-slate-600">/</span>
                            <span className="text-emerald-400 font-semibold">{posPct}% Pos</span>
                          </div>
                          <div className="w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden flex mt-1">
                            <div style={{ width: `${posPct}%` }} className="bg-emerald-500" />
                            <div style={{ width: `${neuPct}%` }} className="bg-indigo-500" />
                            <div style={{ width: `${negPct}%` }} className="bg-rose-500" />
                          </div>
                        </div>
                      </div>

                      {/* Main Complaint Box */}
                      <div className="p-3 rounded-lg bg-rose-500/[0.06] border border-rose-500/20 text-xs space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-rose-300 font-mono flex items-center gap-1">
                          <ShieldAlert className="w-3 h-3" /> Main Customer Complaint:
                        </span>
                        <p className="text-slate-200 font-medium leading-snug">{complaint}</p>
                      </div>

                      {/* AI Summary */}
                      <div className="text-xs text-slate-300 leading-relaxed font-sans">
                        <span className="text-cyan-400 font-semibold">AI Synthesis: </span>
                        {summary}
                      </div>

                      {/* Key Observations */}
                      {observations.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                            Key Observations:
                          </span>
                          <ul className="space-y-1 text-xs text-slate-300">
                            {observations.map((obs, oIdx) => (
                              <li key={oIdx} className="flex items-start gap-1.5">
                                <span className="text-violet-400 mt-1">•</span>
                                <span>{obs}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Representative Customer Feedback Quotes */}
                      {reps.length > 0 && (
                        <div className="p-2.5 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1 font-mono">
                            <Quote className="w-3 h-3 text-cyan-400" /> Supporting Evidence:
                          </span>
                          <p className="text-[11px] text-slate-300 italic font-mono leading-relaxed truncate">
                            "{reps[0]}"
                          </p>
                        </div>
                      )}
                    </div>

                    {/* AI Recommendation Box */}
                    <div className="p-3 rounded-lg bg-cyan-500/[0.06] border border-cyan-500/25 text-xs space-y-0.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-300 font-mono flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Recommended Engineering Action:
                      </span>
                      <p className="text-cyan-100 font-medium leading-snug">{rec}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Bottom Insights Grid: Emerging Problems & Common Complaints */}
          {insights && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-4">
              {/* Emerging Problems */}
              <div className="p-5 rounded-xl surface-card space-y-3">
                <div className="flex items-center gap-1.5 text-amber-400 font-bold text-xs uppercase tracking-wider">
                  <Flame className="w-4 h-4" />
                  <span>Emerging Blocker Alerts</span>
                </div>
                <div className="space-y-2.5">
                  {insights.emerging_problems?.map((item, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-[#111726] border border-border-muted space-y-1">
                      <h4 className="text-xs font-semibold text-slate-100">{item.title}</h4>
                      <p className="text-xs text-slate-400 leading-snug">{item.description}</p>
                      <p className="text-[11px] text-amber-300 font-medium mt-1">
                        Suggested: {item.suggested_action}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actionable Engineering Recommendations */}
              <div className="p-5 rounded-xl surface-card space-y-3">
                <div className="flex items-center gap-1.5 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Sprint Action Items</span>
                </div>
                <div className="space-y-2.5">
                  {insights.actionable_recommendations?.map((item, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-[#111726] border border-border-muted flex items-start gap-2.5">
                      <div className="w-5 h-5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center justify-center font-bold text-[11px] shrink-0 font-mono mt-0.5">
                        {idx + 1}
                      </div>
                      <div className="space-y-0.5">
                        <h4 className="text-xs font-semibold text-slate-100">{item.title}</h4>
                        <p className="text-xs text-slate-400 leading-snug">{item.description}</p>
                        <p className="text-[11px] text-cyan-300 font-medium">{item.suggested_action}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
