# Vocabulary quiz

A 10-question, 7-seconds-per-question vocab quiz with difficulty levels (Easy / Medium / Hard) and per-difficulty Supabase leaderboards. Picks random questions from a pool of 25,000 IELTS-style items spanning English levels 1–6.

## Question selection per difficulty

Each game pulls exactly 10 questions in this distribution:

| Difficulty | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| Easy | 6 | 3 | 1 | – | – | – |
| Medium | – | 1 | 3 | 4 | 2 | – |
| Hard | – | – | 1 | 2 | 4 | 3 |

The mixes overlap by a level on each end so each difficulty has occasional curveballs without crossing into unfair territory.

## Supabase setup

### First-time setup (fresh project)

In the Supabase dashboard, open **SQL Editor** and run:

```sql
create table quiz_scores (
  id bigint generated always as identity primary key,
  player_name text not null check (char_length(player_name) between 1 and 20),
  score integer not null check (score between 0 and 10),
  difficulty text check (difficulty in ('easy', 'medium', 'hard')),
  level_summary text,
  created_at timestamptz default now() not null
);

create index quiz_scores_leaderboard_idx
  on quiz_scores (difficulty, score desc, created_at asc);

alter table quiz_scores enable row level security;

create policy "public_read" on quiz_scores
  for select to anon using (true);

create policy "public_insert" on quiz_scores
  for insert to anon with check (true);
```

### Already have the table from an earlier version

Run only the migration:

```sql
alter table quiz_scores
  add column if not exists difficulty text
  check (difficulty in ('easy', 'medium', 'hard'));

create index if not exists quiz_scores_leaderboard_idx
  on quiz_scores (difficulty, score desc, created_at asc);
```

Existing rows will have `null` difficulty and won't appear in the per-difficulty leaderboards (they're legacy). To backfill them to a default, add this:

```sql
update quiz_scores set difficulty = 'medium' where difficulty is null;
```

### Plug credentials into the app

Edit `config.js`:

```js
window.QUIZ_CONFIG = {
  SUPABASE_URL: 'https://YOUR_PROJECT.supabase.co',
  SUPABASE_ANON_KEY: 'YOUR_ANON_KEY',
  TABLE_NAME: 'quiz_scores',
  LEADERBOARD_LIMIT: 10,
};
```

Both values are public — RLS policies above are what protect your data, not key secrecy. If you skip this, the app still runs but the leaderboard shows a "set up Supabase" hint.

## Local preview

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Don't open `index.html` directly with `file://` — `fetch('questions.json')` is blocked on file URLs.

## Publish to GitHub

```bash
cd vocab-quiz
git init -b main
git add .
git commit -m "Initial commit"
gh repo create vocab-quiz --public --source=. --push
```

If you already pushed an earlier version:

```bash
git add .
git commit -m "Add difficulty selector and per-difficulty leaderboards"
git push
```

## Deploy to Vercel

**Dashboard:** https://vercel.com/new → Import the repo → Framework preset **Other** → Deploy. Auto-redeploys on every push.

**CLI:** `npx vercel --prod`

## Files

- `index.html` — game UI + difficulty selector + leaderboard with tabs
- `config.js` — Supabase credentials
- `questions.json` — 25,000-question pool, minified (~3.3 MB, cached 24h)
- `vercel.json` — caching headers
- `.gitignore` — standard

## Notes on the leaderboard

- Three tabs: Easy / Medium / Hard. Each shows top 10 scores for that difficulty.
- The default tab on landing is whatever difficulty you last selected.
- After finishing a game, the home screen opens with the leaderboard tab matching the difficulty you just played.
- One row per attempt; the same player can appear multiple times.
- Order: `score DESC, created_at ASC` (earlier scores rank higher on ties).
