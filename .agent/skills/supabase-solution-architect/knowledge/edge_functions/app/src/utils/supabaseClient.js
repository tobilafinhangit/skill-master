import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL ?? 'http://localhost:54321',
  process.env.REACT_APP_SUPABASE_ANON_KEY ??
  'YOUR_ANON_KEY'
)
