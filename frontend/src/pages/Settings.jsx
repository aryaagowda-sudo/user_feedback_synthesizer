import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Key, 
  Server, 
  Copy, 
  Check, 
  ShieldCheck, 
  RefreshCw, 
  CheckCircle2, 
  ExternalLink,
  Code2,
  Terminal,
  Shield,
  Layers,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';

const SQL_SCHEMA = `-- FeedbackIQ — Supabase PostgreSQL Schema & Row Level Security
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);

-- 2. Analysis History Table
CREATE TABLE IF NOT EXISTS public.analysis_history (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    analysis_name TEXT NOT NULL,
    total_feedback INTEGER DEFAULT 0 NOT NULL,
    positive_count INTEGER DEFAULT 0 NOT NULL,
    negative_count INTEGER DEFAULT 0 NOT NULL,
    neutral_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.analysis_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own analyses" ON public.analysis_history FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');
CREATE POLICY "Users can delete own analyses" ON public.analysis_history FOR DELETE USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

-- 3. Themes Table
CREATE TABLE IF NOT EXISTS public.themes (
    id TEXT PRIMARY KEY,
    analysis_id TEXT REFERENCES public.analysis_history(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    theme_name TEXT NOT NULL,
    summary TEXT,
    mention_count INTEGER DEFAULT 0 NOT NULL,
    positive_percentage FLOAT DEFAULT 0.0,
    negative_percentage FLOAT DEFAULT 0.0,
    neutral_percentage FLOAT DEFAULT 0.0,
    severity TEXT DEFAULT 'Low',
    priority TEXT DEFAULT 'Medium',
    recommendation TEXT,
    main_complaint TEXT,
    key_observations JSONB DEFAULT '[]'::jsonb,
    representative_feedback JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.themes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own themes" ON public.themes FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

-- 4. Feedback Records Table
CREATE TABLE IF NOT EXISTS public.feedback (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    analysis_id TEXT REFERENCES public.analysis_history(id) ON DELETE CASCADE,
    feedback_text TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    sentiment_confidence FLOAT NOT NULL,
    theme_id TEXT,
    source TEXT DEFAULT 'Web App',
    rating INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own feedback" ON public.feedback FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');`;

export default function Settings() {
  const [copied, setCopied] = useState(false);
  const [health, setHealth] = useState({ online: true, mode: 'Local Mode', records: 30, analyses: 1 });

  useEffect(() => {
    api.getHealth()
      .then(res => setHealth(res))
      .catch(err => console.error(err));
  }, []);

  const handleCopySchema = () => {
    navigator.clipboard.writeText(SQL_SCHEMA);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200 max-w-5xl mx-auto">
      {/* Header */}
      <div className="pb-3 hairline-b">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold tracking-tight text-white">System Settings, Database & AI Models</h1>
          <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">
            Configuration
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          Configure Supabase PostgreSQL persistence, Generative AI credentials, Row Level Security, and deployment parameters.
        </p>
      </div>

      {/* Database Mode Status */}
      <div className="p-5 rounded-xl surface-card space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-violet-600/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Database Engine Status</h2>
              <p className="text-[11px] text-slate-400">PostgreSQL with Row Level Security (RLS) & Local Dev Sandbox</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#080B11] border border-border-muted text-xs font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-slate-300 font-medium text-[11px]">{health.mode || 'Local Development Mode'}</span>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#080B11] border border-border-muted text-xs text-slate-300 leading-relaxed font-sans">
          <p>
            <span className="text-cyan-300 font-semibold">Zero-Config Local Development Mode Active: </span> 
            FeedbackIQ is persisting all customer transcripts, embeddings, and synthesized clusters to <code className="text-violet-300 font-mono">backend/data/local_db.json</code>.
            To connect to a live Supabase PostgreSQL database, configure <code className="text-violet-300 font-mono">SUPABASE_URL</code> and <code className="text-violet-300 font-mono">SUPABASE_SERVICE_ROLE_KEY</code> in <code className="text-slate-400 font-mono">backend/.env</code> and <code className="text-violet-300 font-mono">VITE_SUPABASE_URL</code> / <code className="text-violet-300 font-mono">VITE_SUPABASE_ANON_KEY</code> in <code className="text-slate-400 font-mono">frontend/.env</code>.
          </p>
        </div>
      </div>

      {/* Environment Variables Reference */}
      <div className="p-5 rounded-xl surface-card space-y-3">
        <div className="flex items-center gap-2">
          <Key className="w-4 h-4 text-violet-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Required Environment Variables Reference</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Backend Supabase URL</span>
            <p className="text-cyan-300 truncate">SUPABASE_URL=https://xyz.supabase.co</p>
            <span className="text-[10px] text-slate-500">PostgreSQL REST Endpoint</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Backend Service Role Key</span>
            <p className="text-cyan-300 truncate">SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...</p>
            <span className="text-[10px] text-slate-500">Privileged key for backend writes</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Generative LLM Key</span>
            <p className="text-violet-300 truncate">LLM_API_KEY=AIzaSy... / sk-proj-...</p>
            <span className="text-[10px] text-slate-500">Powers generative summaries & RAG chat</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">LLM Model Name</span>
            <p className="text-violet-300 truncate">LLM_MODEL=gemini-1.5-flash</p>
            <span className="text-[10px] text-slate-500">e.g. gemini-1.5-flash, gpt-4o-mini</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Frontend Supabase URL</span>
            <p className="text-emerald-300 truncate">VITE_SUPABASE_URL=https://xyz.supabase.co</p>
            <span className="text-[10px] text-slate-500">Client-side authentication endpoint</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080B11] border border-border-muted space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Frontend Anon Key</span>
            <p className="text-emerald-300 truncate">VITE_SUPABASE_ANON_KEY=eyJhbGciOi...</p>
            <span className="text-[10px] text-slate-500">Safe public anon key for frontend auth</span>
          </div>
        </div>
      </div>

      {/* SQL Schema Viewer */}
      <div className="p-5 rounded-xl surface-card space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Supabase SQL Schema (4 Tables + RLS)</h2>
          </div>
          <button
            onClick={handleCopySchema}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#080B11] border border-border-muted hover:border-slate-700 text-xs font-semibold text-slate-300 transition-colors font-mono"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            <span>{copied ? 'Copied SQL' : 'Copy Schema'}</span>
          </button>
        </div>

        <pre className="p-3.5 rounded-lg bg-[#080B11] border border-border-muted text-[11px] font-mono text-slate-300 overflow-x-auto max-h-64 leading-relaxed">
          {SQL_SCHEMA}
        </pre>
      </div>

      {/* Deployment Guidance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="p-5 rounded-xl surface-card space-y-1.5">
          <div className="flex items-center gap-2 text-cyan-400 font-bold text-xs uppercase">
            <Server className="w-3.5 h-3.5" />
            <span>Frontend: Deployable on Vercel</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Deploy the <code className="text-white font-mono">frontend/</code> directory directly to Vercel. Set <code className="text-cyan-300 font-mono">VITE_API_URL</code> pointing to your Render backend API.
          </p>
        </div>

        <div className="p-5 rounded-xl surface-card space-y-1.5">
          <div className="flex items-center gap-2 text-violet-400 font-bold text-xs uppercase">
            <Terminal className="w-3.5 h-3.5" />
            <span>Backend: Deployable on Render</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Deploy as a Web Service on Render using Python 3.13. Start command: <code className="text-white font-mono">uvicorn backend.main:app --host 0.0.0.0 --port $PORT</code>.
          </p>
        </div>
      </div>
    </div>
  );
}
