// Supabase config.
// These values are PUBLIC by design — the anon/publishable key is shipped to
// every browser that loads the page. Your data is protected by Row-Level
// Security policies in the database, not by keeping these strings secret.
// See README.md for the one-time table + RLS setup.

window.QUIZ_CONFIG = {
  SUPABASE_URL: 'https://ptcjkgpupdornyyzowkt.supabase.co',
  SUPABASE_ANON_KEY: 'sb_publishable_hXaqpi8SuwF03vYyfpgqBw_NgLDisks',
  TABLE_NAME: 'quiz_scores',
  LEADERBOARD_LIMIT: 10,
};
