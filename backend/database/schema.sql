-- ====================================================================
-- FeedbackIQ — User Feedback Synthesizer
-- Supabase PostgreSQL Schema, Relational Integrity & RLS Policies
-- ====================================================================

-- 1. Enable Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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

-- Trigger to automatically synchronize new Supabase auth users to public.profiles
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


-- 3. Analyses Table (Primary analysis sessions)
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

ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own analyses or public samples"
    ON public.analyses FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can insert their own analyses"
    ON public.analyses FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can update their own analyses"
    ON public.analyses FOR UPDATE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can delete their own analyses"
    ON public.analyses FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');


-- 4. Analysis History Table (Historical audit log of sessions)
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

ALTER TABLE public.analysis_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own history"
    ON public.analysis_history FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can insert into history"
    ON public.analysis_history FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can delete their history"
    ON public.analysis_history FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');


-- 5. Themes Table (Clustered Topics & AI Summaries)
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
    recommendation TEXT,
    main_complaint TEXT,
    is_feature_request BOOLEAN DEFAULT FALSE,
    key_observations JSONB DEFAULT '[]'::jsonb,
    representative_feedback JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (analysis_id, id)
);

ALTER TABLE public.themes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view themes from their own analyses"
    ON public.themes FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can insert themes for their analyses"
    ON public.themes FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can delete their own themes"
    ON public.themes FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');


-- 6. Feedback Table (Individual customer feedback entries)
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

ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view feedback from their own analyses"
    ON public.feedback FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can insert feedback records"
    ON public.feedback FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');

CREATE POLICY "Users can delete feedback from their analyses"
    ON public.feedback FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL OR auth.role() = 'service_role');


-- 7. High-Performance Query Indexes
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
