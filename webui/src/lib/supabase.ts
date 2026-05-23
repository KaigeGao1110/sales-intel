import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://sedwocbnyneberhsuhdr.supabase.co'
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_KL__mprkA_fYdDcH4Ve2HQ_KtSz_aoR'

export const supabase = createClient(supabaseUrl, supabaseKey)
