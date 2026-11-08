-- ====================================================================
-- FeedbackIQ — User Feedback Synthesizer
-- Supabase PostgreSQL Schema & Row Level Security (RLS) Policies
-- ====================================================================

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Profiles Table (User accounts linked to Supabase Auth)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);


-- 3. Analysis History Table (Historical analysis sessions)
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

CREATE POLICY "Users can view their own analyses or public samples"
    ON public.analysis_history FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

CREATE POLICY "Users can create their own analysis sessions"
    ON public.analysis_history FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

CREATE POLICY "Users can delete their own analyses"
    ON public.analysis_history FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');


-- 4. Themes Table (Identified Feedback Clusters & AI Summaries)
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
    severity TEXT DEFAULT 'Low', -- 'Critical', 'High', 'Medium', 'Low'
    priority TEXT DEFAULT 'Medium', -- 'Critical', 'High', 'Medium', 'Low'
    recommendation TEXT,
    main_complaint TEXT,
    key_observations JSONB DEFAULT '[]'::jsonb,
    representative_feedback JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.themes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view themes from their own analyses"
    ON public.themes FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

CREATE POLICY "Users can insert themes for their analyses"
    ON public.themes FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

CREATE POLICY "Users can delete their own themes"
    ON public.themes FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');


-- 5. Feedback Table (Individual customer feedback entries)
CREATE TABLE IF NOT EXISTS public.feedback (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    analysis_id TEXT REFERENCES public.analysis_history(id) ON DELETE CASCADE,
    feedback_text TEXT NOT NULL,
    sentiment TEXT NOT NULL, -- 'Positive', 'Negative', 'Neutral'
    sentiment_confidence FLOAT NOT NULL,
    theme_id TEXT,
    source TEXT DEFAULT 'Web App',
    rating INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view feedback from their own analyses"
    ON public.feedback FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

CREATE POLICY "Users can insert feedback records"
    ON public.feedback FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

CREATE POLICY "Users can delete feedback from their analyses"
    ON public.feedback FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'anon');

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_feedback_analysis_id ON public.feedback(analysis_id);
CREATE INDEX IF NOT EXISTS idx_feedback_sentiment ON public.feedback(sentiment);
CREATE INDEX IF NOT EXISTS idx_feedback_theme_id ON public.feedback(theme_id);
CREATE INDEX IF NOT EXISTS idx_themes_analysis_id ON public.themes(analysis_id);
CREATE INDEX IF NOT EXISTS idx_analysis_history_user_id ON public.analysis_history(user_id);
