/**
 * STRYDER AI — Supabase Client (Frontend)
 * =========================================
 * Initializes the Supabase client for frontend use.
 * Uses the anon key for read-only access via RLS.
 * 
 * Env vars required in frontend/.env:
 *   VITE_SUPABASE_URL=https://your-project.supabase.co
 *   VITE_SUPABASE_ANON_KEY=your-anon-key
 */
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.warn('[SUPABASE] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY — realtime features disabled');
}

export const supabase = (SUPABASE_URL && SUPABASE_ANON_KEY)
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
        realtime: { params: { eventsPerSecond: 10 } },
    })
    : null;

export default supabase;
