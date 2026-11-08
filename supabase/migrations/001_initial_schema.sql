-- ====================================================================
-- FeedbackIQ — User Feedback Synthesizer
-- Migration: 001_initial_schema.sql
-- Description: Complete initial database schema for Supabase PostgreSQL.
-- Includes: profiles, analyses, feedback, themes, analysis_history,
-- foreign keys with CASCADE delete, indexes, and Row Level Security (RLS).
-- ====================================================================

-- Enable UUID & cryptographic extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ====================================================================
-- 1. PROFILES TABLE
-- Linked to Supabase Auth (auth.users)
-- ====================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Profiles RLS Policies
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile" 
    ON public.profiles FOR SELECT 
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert their own profile" ON public.profiles;
CREATE POLICY "Users can insert their own profile" 
    ON public.profiles FOR INSERT 
    WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile" 
    ON public.profiles FOR UPDATE 
    USING (auth.uid() = id);

-- Trigger to automatically create a public.profiles row when a user signs up via Supabase Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name)
  VALUES (
    NEW.id, 
    NEW.email, 
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    full_name = COALESCE(EXCLUDED.full_name, public.profiles.full_name);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT OR UPDATE ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ====================================================================
-- 2. ANALYSES TABLE
-- Primary master record for each analysis session run
-- ====================================================================
CREATE TABLE IF NOT EXISTS public.analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    analysis_name TEXT NOT NULL,
    total_feedback INTEGER DEFAULT 0 NOT NULL,
    positive_count INTEGER DEFAULT 0 NOT NULL,
    negative_count INTEGER DEFAULT 0 NOT NULL,
    neutral_count INTEGER DEFAULT 0 NOT NULL,
    positive_percentage FLOAT DEFAULT 0.0,
    negative_percentage FLOAT DEFAULT 0.0,
    neutral_percentage FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on analyses
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

-- Analyses RLS Policies
DROP POLICY IF EXISTS "Users can view their own analyses or public samples" ON public.analyses;
CREATE POLICY "Users can view their own analyses or public samples" 
    ON public.analyses FOR SELECT 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can insert their own analyses" ON public.analyses;
CREATE POLICY "Users can insert their own analyses" 
    ON public.analyses FOR INSERT 
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can update their own analyses" ON public.analyses;
CREATE POLICY "Users can update their own analyses" 
    ON public.analyses FOR UPDATE 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can delete their own analyses" ON public.analyses;
CREATE POLICY "Users can delete their own analyses" 
    ON public.analyses FOR DELETE 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

-- ====================================================================
-- 3. ANALYSIS_HISTORY TABLE
-- Audit history and session catalog for quick retrieval
-- ====================================================================
CREATE TABLE IF NOT EXISTS public.analysis_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES public.analyses(id) ON DELETE CASCADE,
    analysis_name TEXT NOT NULL,
    total_feedback INTEGER DEFAULT 0 NOT NULL,
    positive_percentage FLOAT DEFAULT 0.0,
    negative_percentage FLOAT DEFAULT 0.0,
    neutral_percentage FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on analysis_history
ALTER TABLE public.analysis_history ENABLE ROW LEVEL SECURITY;

-- Analysis History RLS Policies
DROP POLICY IF EXISTS "Users can view their own history" ON public.analysis_history;
CREATE POLICY "Users can view their own history" 
    ON public.analysis_history FOR SELECT 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can insert into history" ON public.analysis_history;
CREATE POLICY "Users can insert into history" 
    ON public.analysis_history FOR INSERT 
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can delete their history" ON public.analysis_history;
CREATE POLICY "Users can delete their history" 
    ON public.analysis_history FOR DELETE 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

-- ====================================================================
-- 4. THEMES TABLE
-- Clustered feedback topics, metrics, AI summaries, and recommendations
-- ====================================================================
CREATE TABLE IF NOT EXISTS public.themes (
    id TEXT NOT NULL,
    analysis_id UUID REFERENCES public.analyses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    theme_name TEXT NOT NULL,
    summary TEXT,
    mention_count INTEGER DEFAULT 0 NOT NULL,
    positive_percentage FLOAT DEFAULT 0.0,
    negative_percentage FLOAT DEFAULT 0.0,
    neutral_percentage FLOAT DEFAULT 0.0,
    severity TEXT DEFAULT 'Medium', -- 'Critical', 'High', 'Medium', 'Low'
    priority TEXT DEFAULT 'Medium', -- 'Critical', 'High', 'Medium', 'Low'
    priority_score FLOAT DEFAULT 0.0,
    recommendation TEXT,
    main_complaint TEXT,
    is_feature_request BOOLEAN DEFAULT FALSE,
    key_observations JSONB DEFAULT '[]'::jsonb,
    representative_feedback JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (analysis_id, id)
);

-- Enable RLS on themes
ALTER TABLE public.themes ENABLE ROW LEVEL SECURITY;

-- Themes RLS Policies
DROP POLICY IF EXISTS "Users can view themes from their own analyses" ON public.themes;
CREATE POLICY "Users can view themes from their own analyses" 
    ON public.themes FOR SELECT 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can insert themes for their analyses" ON public.themes;
CREATE POLICY "Users can insert themes for their analyses" 
    ON public.themes FOR INSERT 
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can delete their own themes" ON public.themes;
CREATE POLICY "Users can delete their own themes" 
    ON public.themes FOR DELETE 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

-- ====================================================================
-- 5. FEEDBACK TABLE
-- Granular feedback submissions with sentiment & theme classification
-- ====================================================================
CREATE TABLE IF NOT EXISTS public.feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID REFERENCES public.analyses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    feedback_text TEXT NOT NULL,
    sentiment TEXT NOT NULL, -- 'Positive', 'Negative', 'Neutral'
    sentiment_confidence FLOAT NOT NULL,
    theme_id TEXT,
    source TEXT DEFAULT 'Web App',
    rating INTEGER,
    date TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on feedback
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- Feedback RLS Policies
DROP POLICY IF EXISTS "Users can view feedback from their own analyses" ON public.feedback;
CREATE POLICY "Users can view feedback from their own analyses" 
    ON public.feedback FOR SELECT 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can insert feedback records" ON public.feedback;
CREATE POLICY "Users can insert feedback records" 
    ON public.feedback FOR INSERT 
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "Users can delete feedback from their analyses" ON public.feedback;
CREATE POLICY "Users can delete feedback from their analyses" 
    ON public.feedback FOR DELETE 
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

-- ====================================================================
-- 6. HIGH-PERFORMANCE INDEXES
-- Optimized for fast filtering, aggregation, and cascade lookups
-- ====================================================================
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON public.analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON public.analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_history_analysis_id ON public.analysis_history(analysis_id);
CREATE INDEX IF NOT EXISTS idx_analysis_history_user_id ON public.analysis_history(user_id);
CREATE INDEX IF NOT EXISTS idx_themes_analysis_id ON public.themes(analysis_id);
CREATE INDEX IF NOT EXISTS idx_themes_user_id ON public.themes(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_analysis_id ON public.feedback(analysis_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON public.feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_sentiment ON public.feedback(sentiment);
CREATE INDEX IF NOT EXISTS idx_feedback_theme_id ON public.feedback(theme_id);
