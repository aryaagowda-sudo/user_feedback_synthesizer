import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

const isConfigured = Boolean(
  supabaseUrl && 
  supabaseAnonKey && 
  !supabaseUrl.startsWith('https://your-project-id') &&
  !supabaseAnonKey.startsWith('your-')
);

export const supabase = isConfigured ? createClient(supabaseUrl, supabaseAnonKey) : null;
export const isSupabaseConfigured = isConfigured;
