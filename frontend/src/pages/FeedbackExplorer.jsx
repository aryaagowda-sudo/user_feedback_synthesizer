import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  ArrowUpDown, 
  ChevronLeft, 
  ChevronRight, 
  Download, 
  Smile, 
  Frown, 
  Minus,
  Sparkles,
  X,
  ExternalLink,
  Layers,
  Calendar,
  Smartphone,
  Copy,
  Check,
  Code2
} from 'lucide-react';
import { api } from '../services/api';

export default function FeedbackExplorer() {
  const [feedbackList, setFeedbackList] = useState([]);
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [sentiment, setSentiment] = useState(() => {
    const saved = sessionStorage.getItem('explorer_sentiment_filter');
    if (saved) {
      sessionStorage.removeItem('explorer_sentiment_filter');
      return saved;
    }
    return 'All';
  });
  const [themeFilter, setThemeFilter] = useState(() => {
    const saved = sessionStorage.getItem('explorer_theme_filter');
    if (saved) {
      sessionStorage.removeItem('explorer_theme_filter');
      return saved;
    }
    return 'All';
  });
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const limit = 15;

  // Detail Drawer
  const [selectedItem, setSelectedItem] = useState(null);
  const [copiedJson, setCopiedJson] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const [correctionSaved, setCorrectionSaved] = useState(false);

  const handleCorrectSentiment = async (newSent) => {
    if (!selectedItem) return;
    setCorrecting(true);
    try {
      await api.correctFeedbackLabel({
        feedback_id: selectedItem.id,
        feedback_text: selectedItem.feedback_text,
        corrected_sentiment: newSent,
        original_sentiment: selectedItem.sentiment,
        corrected_by: 'ML Engineer'
      });
      setSelectedItem(prev => ({ ...prev, sentiment: newSent }));
      setFeedbackList(prev => prev.map(it => it.id === selectedItem.id ? { ...it, sentiment: newSent } : it));
      setCorrectionSaved(true);
      setTimeout(() => setCorrectionSaved(false), 3000);
    } catch (err) {
      alert('Failed to save correction: ' + err.message);
    } finally {
      setCorrecting(false);
    }
  };

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const res = await api.getFeedback({
        search: search || undefined,
        sentiment: sentiment !== 'All' ? sentiment : undefined,
        theme_id: themeFilter !== 'All' ? themeFilter : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        limit
      });
      setFeedbackList(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load feedback records:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchThemes = async () => {
    try {
      const res = await api.getThemes();
      setThemes(res.themes || []);
    } catch (err) {
      console.error('Failed to load themes:', err);
    }
  };

  useEffect(() => {
    fetchThemes();
  }, []);

  useEffect(() => {
    fetchRecords();
  }, [search, sentiment, themeFilter, sortBy, sortOrder, page]);

  const totalPages = Math.ceil(total / limit) || 1;

  const exportCSV = () => {
    if (!feedbackList.length) return;
    const headers = ["ID", "Feedback", "Sentiment", "Confidence", "Theme", "Rating", "Date", "Source"];
    const rows = feedbackList.map(item => [
      item.id,
      `"${item.feedback_text.replace(/"/g, '""')}"`,
      item.sentiment,
      item.confidence,
      `"${item.theme_name || ''}"`,
      item.rating || '',
      item.date,
      item.source
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `feedbackiq_records_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const copyJson = (item) => {
    navigator.clipboard.writeText(JSON.stringify(item, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 hairline-b">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white">Feedback Explorer</h1>
            <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              {total} Total Records
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Filter, inspect, and analyze individual customer submissions and their model-assigned themes.
          </p>
        </div>

        <button
          onClick={exportCSV}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0E131F] border border-border-muted hover:border-slate-700 text-xs font-semibold text-slate-300 hover:text-white transition-colors w-fit"
        >
          <Download className="w-3.5 h-3.5 text-cyan-400" />
          <span>Export Filtered CSV</span>
        </button>
      </div>

      {/* Filter and Search Bar (Linear Style) */}
      <div className="p-3.5 rounded-xl surface-card space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          {/* Search Box */}
          <div className="relative md:col-span-5">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter feedback by text, keywords, or source..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full bg-[#080B11] border border-border-muted rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/80 transition-colors"
            />
          </div>

          {/* Sentiment Filter Tabs */}
          <div className="md:col-span-4 flex items-center gap-1 bg-[#080B11] p-1 rounded-lg border border-border-muted text-xs">
            {['All', 'Positive', 'Negative', 'Neutral'].map((s) => (
              <button
                key={s}
                onClick={() => { setSentiment(s); setPage(1); }}
                className={`flex-1 py-1 text-center rounded font-medium text-[11px] transition-colors ${
                  sentiment === s 
                    ? 'bg-slate-800 text-white font-semibold shadow-sm' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Theme Dropdown */}
          <div className="relative md:col-span-3">
            <select
              value={themeFilter}
              onChange={(e) => { setThemeFilter(e.target.value); setPage(1); }}
              className="w-full bg-[#080B11] border border-border-muted rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-violet-500/80 appearance-none transition-colors cursor-pointer truncate"
            >
              <option value="All">All Semantic Clusters</option>
              {themes.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            <Layers className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>

        {/* Sorting Controls */}
        <div className="flex items-center justify-between text-xs text-slate-500 pt-2 hairline-t">
          <div className="flex items-center gap-2">
            <span>Sort by:</span>
            <button 
              onClick={() => { setSortBy('date'); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border ${sortBy === 'date' ? 'bg-violet-600/20 text-violet-300 border-violet-500/40' : 'border-transparent text-slate-400'}`}
            >
              Date {sortBy === 'date' && (sortOrder === 'asc' ? '↑' : '↓')}
            </button>
            <button 
              onClick={() => { setSortBy('confidence'); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border ${sortBy === 'confidence' ? 'bg-violet-600/20 text-violet-300 border-violet-500/40' : 'border-transparent text-slate-400'}`}
            >
              Confidence {sortBy === 'confidence' && (sortOrder === 'asc' ? '↑' : '↓')}
            </button>
          </div>

          <span className="text-[11px] font-mono">
            Showing {feedbackList.length} of {total} items
          </span>
        </div>
      </div>

      {/* Main Table (High Density) */}
      <div className="rounded-xl surface-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="hairline-b bg-white/[0.01] text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                <th className="py-2.5 px-3.5">Customer Comment</th>
                <th className="py-2.5 px-3">Sentiment</th>
                <th className="py-2.5 px-3">Semantic Theme</th>
                <th className="py-2.5 px-3 text-center">Confidence</th>
                <th className="py-2.5 px-3 text-center">Rating</th>
                <th className="py-2.5 px-3">Date</th>
                <th className="py-2.5 px-3">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-muted">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-400">
                    <div className="w-6 h-6 rounded-full border-2 border-violet-500 border-t-transparent animate-spin mx-auto mb-2"></div>
                    Loading feedback transcripts...
                  </td>
                </tr>
              ) : feedbackList.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-400">
                    No feedback records match the current filter criteria.
                  </td>
                </tr>
              ) : (
                feedbackList.map((item) => {
                  const isPos = item.sentiment === 'Positive';
                  const isNeg = item.sentiment === 'Negative';
                  return (
                    <tr 
                      key={item.id}
                      onClick={() => setSelectedItem(item)}
                      className="hover:bg-white/[0.03] cursor-pointer transition-colors group"
                    >
                      <td className="py-2.5 px-3.5 max-w-md">
                        <p className="text-slate-200 group-hover:text-cyan-300 font-medium transition-colors line-clamp-1">
                          {item.feedback_text}
                        </p>
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded ${
                          isPos ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          isNeg ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                          'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${isPos ? 'bg-emerald-400' : isNeg ? 'bg-rose-400' : 'bg-indigo-400'}`} />
                          {item.sentiment}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span className="text-[11px] text-slate-300">
                          {item.theme_name || 'Unassigned'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-center whitespace-nowrap font-mono text-[11px] text-slate-400">
                        {Math.round((item.confidence || 0) * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-center whitespace-nowrap">
                        {item.rating ? (
                          <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-1.5 py-0.2 rounded">
                            ★ {item.rating}
                          </span>
                        ) : (
                          <span className="text-slate-600">-</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                        {item.date}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap text-slate-400 text-[11px]">
                        {item.source}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#0A0D15] hairline-t text-xs text-slate-400">
          <span className="font-mono text-[11px]">Page {page} of {totalPages}</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1 rounded bg-[#0E131F] border border-border-muted hover:border-slate-700 disabled:opacity-40 text-slate-300"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1 rounded bg-[#0E131F] border border-border-muted hover:border-slate-700 disabled:opacity-40 text-slate-300"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Slide-over Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="relative w-full max-w-lg rounded-xl surface-card p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 hairline-b">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Record Details</h3>
              </div>
              <button 
                onClick={() => setSelectedItem(null)}
                className="p-1 text-slate-400 hover:text-white rounded bg-slate-800"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500 uppercase tracking-wider text-[10px] font-bold">Feedback Quote</span>
                <p className="mt-1 p-3 rounded-lg bg-[#080B11] border border-border-muted text-slate-100 text-xs leading-relaxed font-sans">
                  "{selectedItem.feedback_text}"
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="p-2.5 rounded-lg bg-[#111726] border border-border-muted">
                  <span className="text-slate-500 text-[10px] uppercase font-bold">Sentiment Classification</span>
                  <p className="text-xs font-bold text-white mt-0.5">{selectedItem.sentiment}</p>
                  <p className="text-[10px] text-cyan-400 font-mono">Confidence: {Math.round(selectedItem.confidence * 100)}%</p>
                </div>

                <div className="p-2.5 rounded-lg bg-[#111726] border border-border-muted">
                  <span className="text-slate-500 text-[10px] uppercase font-bold">Assigned Cluster</span>
                  <p className="text-xs font-semibold text-slate-200 mt-0.5 truncate">{selectedItem.theme_name}</p>
                  <p className="text-[10px] text-slate-400 font-mono">{selectedItem.theme_id}</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-1 text-center font-mono text-[11px]">
                <div className="p-2 rounded bg-white/[0.02]">
                  <span className="text-[9px] text-slate-500 uppercase">Channel</span>
                  <p className="text-slate-200 mt-0.5 truncate">{selectedItem.source}</p>
                </div>
                <div className="p-2 rounded bg-white/[0.02]">
                  <span className="text-[9px] text-slate-500 uppercase">Date</span>
                  <p className="text-slate-200 mt-0.5">{selectedItem.date}</p>
                </div>
                <div className="p-2 rounded bg-white/[0.02]">
                  <span className="text-[9px] text-slate-500 uppercase">Rating</span>
                  <p className="text-amber-400 mt-0.5">{selectedItem.rating ? `★ ${selectedItem.rating}` : 'N/A'}</p>
                </div>
              </div>

              {/* Human-in-the-loop Ground Truth Annotation */}
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    Correct Sentiment Label (Candidate Pool)
                  </span>
                  {correctionSaved && (
                    <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                      <Check className="w-3 h-3" /> Saved for retraining
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {['Negative', 'Neutral', 'Positive'].map((s) => (
                    <button
                      key={s}
                      disabled={correcting || selectedItem.sentiment === s}
                      onClick={() => handleCorrectSentiment(s)}
                      className={`py-1.5 px-2 rounded-lg text-xs font-medium border transition ${
                        selectedItem.sentiment === s
                          ? s === 'Positive'
                            ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300'
                            : s === 'Negative'
                            ? 'bg-rose-500/20 border-rose-500 text-rose-300'
                            : 'bg-indigo-500/20 border-indigo-500 text-indigo-300'
                          : 'bg-slate-800/40 border-slate-700/60 text-slate-400 hover:text-white hover:border-slate-500'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-3 hairline-t flex items-center justify-between">
              <button
                onClick={() => copyJson(selectedItem)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition-colors font-mono"
              >
                {copiedJson ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedJson ? 'Copied JSON' : 'Copy JSON'}</span>
              </button>

              <button
                onClick={() => setSelectedItem(null)}
                className="px-3 py-1 rounded-lg bg-violet-600 hover:bg-violet-500 text-xs font-semibold text-white transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
