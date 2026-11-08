import React, { useState, useRef, useEffect } from 'react';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  Cpu, 
  Layers, 
  ArrowRight, 
  RefreshCw, 
  FileSpreadsheet, 
  Zap, 
  Database,
  Sliders,
  Check
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

const PIPELINE_STAGES = [
  { id: 1, title: 'Data Preprocessing', desc: 'Trimming whitespace, deduplicating, and validating records' },
  { id: 2, title: 'Sentiment Classification', desc: 'High-throughput DistilBERT batch inference for polarity' },
  { id: 3, title: 'Semantic Embeddings', desc: 'Dense 384-d vector embeddings via all-MiniLM-L6-v2' },
  { id: 4, title: 'Semantic Clustering', desc: 'Partitioning high-dimensional embeddings with K-Means' },
  { id: 5, title: 'Theme Identification', desc: 'Auto-extracting cluster titles & priority rankings' },
  { id: 6, title: 'Theme Summarization', desc: 'Synthesizing evidence-based summaries & recommendations' },
];

export default function AnalyzeFeedback({ onNavigate }) {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('csv'); // 'csv' or 'manual'
  const [file, setFile] = useState(null);
  const [manualText, setManualText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  
  // Real-time background job polling state
  const [loading, setLoading] = useState(false);
  const [currentStageIndex, setCurrentStageIndex] = useState(0); // 1-based index (1 to 6)
  const [currentStageName, setCurrentStageName] = useState('');
  const [progressPct, setProgressPct] = useState(0);
  const [stageMessage, setStageMessage] = useState('');
  const [processedItems, setProcessedItems] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const pollIntervalRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  };

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      validateAndSetFile(selected);
    }
  };

  const validateAndSetFile = (f) => {
    if (!f.name.endsWith('.csv')) {
      setError('Please upload a valid .csv file.');
      setFile(null);
      return;
    }
    setError(null);
    setFile(f);
  };

  const pollJobStatus = (targetJobId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const job = await api.getAnalysisStatus(targetJobId);
        setCurrentStageIndex(job.stage_index || 1);
        setCurrentStageName(job.current_stage || 'Processing');
        setProgressPct(job.progress_percentage || 0);
        setStageMessage(job.message || 'Processing pipeline...');
        setProcessedItems(job.processed_items || 0);
        setTotalItems(job.total_items || 0);

        if (job.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          setLoading(false);
          setResult(job.result);
        } else if (job.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          setLoading(false);
          setError(job.error || job.message || 'Analysis pipeline encountered an error.');
        }
      } catch (err) {
        console.error('Error polling analysis status:', err);
      }
    }, 800);
  };

  const handleAnalyzeCSV = async () => {
    if (!file) {
      setError('Please select or drop a CSV file first.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setProgressPct(5);
    setCurrentStageIndex(1);
    setCurrentStageName('Data Preprocessing');
    setStageMessage(`Uploading ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB) to backend...`);

    try {
      const res = await api.uploadCSV(file, user?.id);
      if (res.job_id) {
        setJobId(res.job_id);
        setStageMessage(res.message || 'Analysis started in background...');
        pollJobStatus(res.job_id);
      } else {
        setResult(res);
        setLoading(false);
      }
    } catch (err) {
      setError(err.message || 'Upload failed. Please check file format.');
      setLoading(false);
    }
  };

  const handleAnalyzeManual = async () => {
    if (!manualText.trim()) {
      setError('Please enter at least one feedback sentence.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setProgressPct(5);
    setCurrentStageIndex(1);
    setCurrentStageName('Data Preprocessing');
    setStageMessage('Submitting records for background analysis...');

    try {
      const res = await api.analyzeRawText(manualText, 'Manual Ingestion', user?.id);
      if (res.job_id) {
        setJobId(res.job_id);
        setStageMessage(res.message || 'Analysis started in background...');
        pollJobStatus(res.job_id);
      } else {
        setResult(res);
        setLoading(false);
      }
    } catch (err) {
      setError(err.message || 'Analysis request failed.');
      setLoading(false);
    }
  };

  const loadSampleDataset = async () => {
    const sampleFeedbacks = [
      "App crashes immediately on the payment confirmation screen on iOS 18",
      "Unable to log in with Google OAuth credentials after the recent update",
      "Login button unresponsive on Firefox browser for desktop",
      "Charged twice for my monthly subscription without receipt or notification",
      "Dark mode contrast is too harsh, text is difficult to read",
      "Would love automated Slack webhook notifications for high severity alerts",
      "Searching through 1000 items causes the entire tab to lag significantly",
      "The automated theme clustering saved our team 15 hours this week"
    ].join("\n");
    setManualText(sampleFeedbacks);
    setActiveTab('manual');
    setError(null);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200 max-w-5xl mx-auto">
      {/* Header */}
      <div className="pb-3 hairline-b">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold tracking-tight text-white">Ingest & Synthesize Customer Feedback</h1>
          <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">
            NLP Ingestion
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          Upload CSV transcripts or paste raw user comments to extract sentiment polarity, embeddings, and prioritized clusters.
        </p>
      </div>

      {/* Mode Selector Tabs */}
      <div className="flex items-center gap-1.5 p-1 rounded-lg bg-[#0E131F] border border-border-muted w-fit text-xs">
        <button
          onClick={() => { setActiveTab('csv'); setError(null); }}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md font-medium transition-colors ${
            activeTab === 'csv' 
              ? 'bg-violet-600 text-white font-semibold shadow-sm' 
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span>Upload CSV</span>
        </button>

        <button
          onClick={() => { setActiveTab('manual'); setError(null); }}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md font-medium transition-colors ${
            activeTab === 'manual' 
              ? 'bg-violet-600 text-white font-semibold shadow-sm' 
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Paste Transcripts</span>
        </button>

        <button
          onClick={loadSampleDataset}
          className="flex items-center gap-1 px-3 py-1.5 rounded-md text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors font-mono text-[11px]"
        >
          <Sparkles className="w-3 h-3" />
          <span>Sample Data</span>
        </button>
      </div>

      {/* Main Grid: Upload Area on Left, Stepper & Live Progress on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Input and Live Progress (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {activeTab === 'csv' ? (
            /* CSV Upload Card */
            <div className="p-5 rounded-xl surface-card space-y-4">
              <div 
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`
                  border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer
                  ${isDragging 
                    ? 'border-violet-500 bg-violet-600/10 scale-[1.01]' 
                    : file 
                      ? 'border-emerald-500/50 bg-emerald-500/[0.04]' 
                      : 'border-border-muted hover:border-slate-600 bg-[#080B11]/50'}
                `}
                onClick={() => document.getElementById('csvFileInput').click()}
              >
                <input 
                  id="csvFileInput"
                  type="file" 
                  accept=".csv"
                  className="hidden"
                  onChange={handleFileChange}
                />

                {file ? (
                  <div className="space-y-2">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                      <Check className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">{file.name}</p>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for AI Pipeline
                      </p>
                    </div>
                    <span className="inline-block text-[10px] text-cyan-400 hover:underline pt-1">
                      Click to choose another CSV file
                    </span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="w-10 h-10 rounded-full bg-violet-600/20 text-violet-400 flex items-center justify-center mx-auto">
                      <UploadCloud className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-200">
                        Drag and drop your customer feedback CSV here
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Supports <code className="text-slate-400">content</code>, <code className="text-slate-400">feedback</code>, <code className="text-slate-400">review</code>, <code className="text-slate-400">score</code>, <code className="text-slate-400">date</code>
                      </p>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-white/[0.06] text-white text-[11px] font-medium border border-white/[0.08]">
                      Browse Files
                    </span>
                  </div>
                )}
              </div>

              {/* Action Button */}
              <button
                onClick={handleAnalyzeCSV}
                disabled={loading || !file}
                className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold shadow-sm transition-all disabled:opacity-40 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-300" />
                    <span>Processing ({progressPct}%)...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5" />
                    <span>Run Full AI Analysis</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            /* Manual Input Area */
            <div className="p-5 rounded-xl surface-card space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-white">Paste Customer Feedback (1 item per line)</label>
                <span className="text-[10px] font-mono text-slate-500">
                  {manualText ? `${manualText.split('\n').filter(Boolean).length} lines` : '0 lines'}
                </span>
              </div>
              <textarea
                rows={8}
                placeholder="Paste customer complaints, reviews, or interview snippets here...
Example:
App crashes immediately on the payment confirmation screen
Login button unresponsive on Firefox browser
Loved the new fast analytics dashboard"
                value={manualText}
                onChange={(e) => setManualText(e.target.value)}
                disabled={loading}
                className="w-full p-3.5 rounded-lg bg-[#080B11] border border-border-muted text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/80 font-mono transition-colors resize-y disabled:opacity-50"
              />
              <button
                onClick={handleAnalyzeManual}
                disabled={loading || !manualText.trim()}
                className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold shadow-sm transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-300" />
                    <span>Processing ({progressPct}%)...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5" />
                    <span>Synthesize Pasted Feedback</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Live Progress Bar Card (Displayed when background task is running) */}
          {loading && (
            <div className="p-4 rounded-xl surface-card border-violet-500/40 bg-violet-950/[0.08] space-y-3 animate-in fade-in duration-150">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span className="text-xs font-bold text-slate-200">
                    Stage {currentStageIndex} of 6: {currentStageName}
                  </span>
                </div>
                <span className="text-xs font-mono font-bold text-cyan-400">
                  {progressPct}%
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-violet-600 via-indigo-500 to-cyan-400 transition-all duration-300 ease-out"
                  style={{ width: `${progressPct}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span className="truncate max-w-sm">{stageMessage}</span>
                {totalItems > 0 && (
                  <span className="shrink-0 text-slate-300 font-medium">
                    {processedItems.toLocaleString()} / {totalItems.toLocaleString()} items
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-xs text-rose-300 animate-in fade-in">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-rose-200">Pipeline Execution Error</p>
                <p className="text-[11px] leading-relaxed text-slate-300">{error}</p>
                <button
                  onClick={() => { setError(null); }}
                  className="text-[10px] text-rose-400 hover:underline font-mono pt-1 inline-block"
                >
                  Dismiss & Try Again
                </button>
              </div>
            </div>
          )}

          {/* Success Result Banner */}
          {result && (
            <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-slate-200 space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-400 font-bold">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="text-sm">Feedback Synthesized Successfully</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/20 px-2.5 py-0.5 rounded-full font-semibold">
                  100% Complete
                </span>
              </div>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1 text-slate-300 font-mono text-[11px]">
                <div className="p-2 rounded-lg bg-[#080B11] border border-border-muted">
                  <span className="text-slate-500 text-[10px] block">PROCESSED</span>
                  <span className="text-white font-bold text-sm">{(result.processed_count || 0).toLocaleString()}</span> items
                </div>
                <div className="p-2 rounded-lg bg-[#080B11] border border-border-muted">
                  <span className="text-slate-500 text-[10px] block">CLUSTERS</span>
                  <span className="text-violet-400 font-bold text-sm">{result.themes_count || 0}</span> themes
                </div>
                <div className="p-2 rounded-lg bg-[#080B11] border border-border-muted col-span-2 sm:col-span-1">
                  <span className="text-slate-500 text-[10px] block">DATASET</span>
                  <span className="text-cyan-400 truncate block text-xs">{result.dataset_name || 'Uploaded File'}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <button
                  onClick={() => onNavigate('dashboard')}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors shadow-sm"
                >
                  View Executive Dashboard
                </button>
                <button
                  onClick={() => onNavigate('insights')}
                  className="px-3.5 py-2 rounded-lg bg-[#0E131F] border border-border-muted hover:border-slate-700 text-slate-200 text-xs transition-colors"
                >
                  AI Summaries →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: 6-Stage AI Pipeline Stepper Visualizer (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-xl surface-card space-y-3">
          <div className="flex items-center justify-between border-b border-border-muted pb-2.5">
            <div className="flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">AI Pipeline Stepper</h3>
            </div>
            {loading && (
              <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                Live Stage {currentStageIndex}/6
              </span>
            )}
          </div>

          <div className="space-y-2">
            {PIPELINE_STAGES.map((stage) => {
              const isActive = loading && currentStageIndex === stage.id;
              const isDone = (!loading && result) || (currentStageIndex > stage.id);

              return (
                <div 
                  key={stage.id} 
                  className={`p-2.5 rounded-lg transition-all border ${
                    isActive 
                      ? 'bg-violet-600/10 border-violet-500/40 shadow-sm' 
                      : isDone 
                        ? 'bg-[#111726] border-emerald-500/20' 
                        : 'bg-[#080B11]/50 border-border-muted opacity-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-slate-200">
                      Stage {stage.id}: {stage.title}
                    </span>
                    {isDone ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    ) : isActive ? (
                      <RefreshCw className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                    ) : (
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
                    )}
                  </div>
                  <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">{stage.desc}</p>
                </div>
              );
            })}
          </div>

          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-border-muted text-[10px] text-slate-400 font-mono space-y-1">
            <p className="text-cyan-300 font-semibold">Asynchronous Background Architecture:</p>
            <p>Non-blocking worker threads process 10,000+ customer reviews without HTTP connection timeouts.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
