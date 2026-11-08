import React, { useState, useEffect } from 'react';
import { 
  FolderGit2, 
  Clock, 
  Trash2, 
  Eye, 
  UploadCloud, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle,
  TrendingUp,
  Layers,
  Database,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function AnalysisHistory({ onNavigate }) {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await api.getHistory(user?.id);
      setHistory(res.history || []);
      const health = await api.getHealth();
      if (res.history?.length > 0) {
        setActiveId(res.history[0].id);
      }
    } catch (err) {
      console.error('Failed to load analysis history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [user]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleActivate = async (id, name) => {
    setActionLoading(true);
    try {
      await api.activateAnalysis(id);
      setActiveId(id);
      showToast(`Activated analysis: ${name}`);
      if (onNavigate) {
        setTimeout(() => onNavigate('dashboard'), 400);
      }
    } catch (err) {
      showToast(`Error activating: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete analysis "${name}"? This will permanently remove its feedback and themes.`)) {
      return;
    }
    setActionLoading(true);
    try {
      await api.deleteAnalysis(id, user?.id);
      showToast(`Deleted analysis: ${name}`);
      await fetchHistory();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200 max-w-6xl mx-auto">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 p-3 rounded-xl surface-card border border-cyan-500/30 text-cyan-300 text-xs shadow-2xl flex items-center gap-2 animate-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-cyan-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 hairline-b">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white">Analysis Sessions History</h1>
            <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">
              Supabase & Local Store
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Review past feedback syntheses, switch active analysis workspaces, or clean up obsolete datasets.
          </p>
        </div>

        <button
          onClick={() => onNavigate && onNavigate('analyze')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-sm transition-colors w-fit"
        >
          <UploadCloud className="w-3.5 h-3.5" />
          <span>Ingest New Dataset</span>
        </button>
      </div>

      {/* Sessions Grid */}
      {loading ? (
        <div className="p-12 rounded-xl surface-card text-center">
          <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-mono">Retrieving historical analysis sessions...</p>
        </div>
      ) : history.length === 0 ? (
        <div className="p-12 rounded-xl surface-card text-center space-y-3">
          <FolderGit2 className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-200">No Previous Analyses Found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            You haven't uploaded or analyzed any feedback datasets yet. Ingest your first CSV file or sample dataset to generate AI themes and insights.
          </p>
          <button
            onClick={() => onNavigate && onNavigate('analyze')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-sm transition-colors"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Your First Dataset</span>
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((session) => {
            const isActive = activeId === session.id;
            const posPct = session.positive_percentage || (session.total_feedback > 0 ? Math.round((session.positive_count / session.total_feedback) * 100) : 0);
            const negPct = session.negative_percentage || (session.total_feedback > 0 ? Math.round((session.negative_count / session.total_feedback) * 100) : 0);
            const neuPct = session.neutral_percentage || (session.total_feedback > 0 ? Math.round((session.neutral_count / session.total_feedback) * 100) : 0);

            return (
              <div
                key={session.id}
                className={`p-4 rounded-xl surface-card transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isActive ? 'border-violet-500/50 bg-violet-950/[0.08]' : 'hover:border-slate-700'
                }`}
              >
                {/* Left: Info */}
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <span className="font-semibold text-sm text-slate-100 truncate">
                      {session.analysis_name}
                    </span>
                    {isActive && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active Workspace
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      {new Date(session.created_at).toLocaleDateString()} {new Date(session.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span>•</span>
                    <span className="text-slate-300 font-medium">
                      {session.total_feedback} items analyzed
                    </span>
                    {session.themes_count > 0 && (
                      <>
                        <span>•</span>
                        <span className="text-violet-300 font-medium">
                          {session.themes_count} themes
                        </span>
                      </>
                    )}
                  </div>

                  {/* Sentiment Bar */}
                  <div className="pt-1.5 flex items-center gap-2 max-w-md">
                    <div className="h-1.5 flex-1 bg-slate-800 rounded-full overflow-hidden flex">
                      <div style={{ width: `${posPct}%` }} className="bg-emerald-500" title={`Positive: ${posPct}%`} />
                      <div style={{ width: `${neuPct}%` }} className="bg-indigo-500" title={`Neutral: ${neuPct}%`} />
                      <div style={{ width: `${negPct}%` }} className="bg-rose-500" title={`Negative: ${negPct}%`} />
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] font-mono shrink-0">
                      <span className="text-emerald-400">{posPct}% Pos</span>
                      <span className="text-slate-500">|</span>
                      <span className="text-rose-400">{negPct}% Neg</span>
                    </div>
                  </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleActivate(session.id, session.analysis_name)}
                    disabled={actionLoading}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                      isActive 
                        ? 'bg-white/[0.08] text-white hover:bg-white/[0.12] border border-white/[0.1]' 
                        : 'bg-violet-600 hover:bg-violet-500 text-white shadow-sm'
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>{isActive ? 'View in Dashboard' : 'Open Analysis'}</span>
                    <ArrowRight className="w-3 h-3 ml-0.5" />
                  </button>

                  <button
                    onClick={() => handleDelete(session.id, session.analysis_name)}
                    disabled={actionLoading}
                    title="Delete this analysis session"
                    className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
