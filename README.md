# Vocabulary quiz

A 10-question, 7-seconds-per-question vocab quiz with a Supabase-backed leaderboard. Picks random questions from a pool of 5000 IELTS-style items spanning levels 1–6.

## One-time Supabase setup

### 1. Create the project

Sign up at [supabase.com](https://supabase.com) and create a new project. Note the project URL and anon key from **Project Settings → API**.

### 2. Create the table

In the Supabase dashboard, open **SQL Editor** and run:

```sql
-- Create the scores table
create table quiz_scores (
  id bigint generated always as identity primary key,
  player_name text not null check (char_length(player_name) between 1 and 20),
  score integer not null check (score between 0 and 10),
  level_summary text,
  created_at timestamptz default now() not null
);

-- Index for fast leaderboard queries
create index quiz_scores_leaderboard_idx
  on quiz_scores (score desc, created_at asc);

-- Enable Row-Level Security
alter table quiz_scores enable row level security;

-- Anyone can read scores (leaderboard is public)
create policy "public_read" on quiz_scores
  for select to anon using (true);

-- Anyone can insert a score (constraints on the table prevent garbage)
create policy "public_insert" on quiz_scores
  for insert to anon with check (true);
```

### 3. Plug the credentials into the app

Edit `config.js` and replace the placeholders:

```js
window.QUIZ_CONFIG = {
  SUPABASE_URL: 'https://abcdefgh.supabase.co',      // your project URL
  SUPABASE_ANON_KEY: 'eyJhbGciOi...',                // your anon (public) key
  TABLE_NAME: 'quiz_scores',
  LEADERBOARD_LIMIT: 10,
};
```

Both values are **public by design** — they ship to the browser. Security comes from the RLS policies above, not the keys.

If you skip this step the app still runs; the leaderboard panel just shows a "set up Supabase" hint.

## Local preview

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

Or `npx serve .`. Don't open `index.html` directly with `file://` — the page fetches `questions.json` and `config.js` on load, and browsers block `fetch` on file URLs.

## Publish to GitHub

```bash
cd vocab-quiz
git init
git add .
git commit -m "Initial commit"
gh repo create vocab-quiz --public --source=. --push
```

If you don't have the `gh` CLI: create the repo on github.com, then:

```bash
git remote add origin https://github.com/<your-username>/vocab-quiz.git
git branch -M main
git push -u origin main
```

## Deploy to Vercel

**Option A — dashboard (auto-deploys on every push):**

1. Go to https://vercel.com/new
2. Import the `vocab-quiz` repo
3. Framework preset: **Other** (no build needed)
4. Click Deploy

**Option B — CLI:**

```bash
npm i -g vercel
vercel --prod
```

## Files

- `index.html` — game UI, fetches questions and talks to Supabase
- `config.js` — Supabase credentials (edit this with your values)
- `questions.json` — 5000-question pool, minified (~650 KB)
- `vercel.json` — caching headers
- `.gitignore` — standard ignores

## Notes on the leaderboard

- One row per attempt (a player can appear multiple times if they play more than once)
- Ordered by `score` descending, then `created_at` ascending (earlier scores rank higher on ties)
- Player name is stored in `localStorage` so it pre-fills on the next attempt
- No rate limiting; if abuse becomes an issue, add a Supabase Edge Function or tighten the RLS policy (e.g., require a JWT)
