# Vocabulary Quiz

A timed English vocabulary quiz with Easy / Medium / Hard difficulty levels, per-difficulty Supabase leaderboards, and a curated 12,000-question bank spanning CEFR L1–L6 (A1 → C2).

## Layout

```
vocab-quiz/
├── index.html          The game (UI + logic + leaderboard)
├── config.js           Supabase credentials
├── questions.json      12k pool, compact format (app runtime)
├── vercel.json         Static deploy config
├── data/               Source bank (canonical, full schema)
│   ├── level_1.json    2,000 A1 / Beginner
│   ├── level_2.json    2,000 A2 / Elementary
│   ├── level_3.json    2,000 B1 / Intermediate
│   ├── level_4.json    2,000 B2 / Upper-intermediate
│   ├── level_5.json    2,000 C1 / Advanced
│   ├── level_6.json    2,000 C2 / Proficiency
│   └── all_levels.json 12,000 consolidated, full schema
├── .gitignore
└── README.md
```

`data/*.json` preserves the original schema (strings everywhere). `questions.json` at root is a compact-keyed version (`i`, `q`, `o`, `l`, `c`) that the app fetches at load time.

## Difficulty mix

| Difficulty | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| Easy | 6 | 3 | 1 | – | – | – |
| Medium | – | 1 | 3 | 4 | 2 | – |
| Hard | – | – | 1 | 2 | 4 | 3 |

Each game is exactly 10 questions in this distribution, no level repeats within a session.

## Supabase setup

### Fresh project

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

### Adding `difficulty` to an existing table

```sql
alter table quiz_scores
  add column if not exists difficulty text
  check (difficulty in ('easy', 'medium', 'hard'));

create index if not exists quiz_scores_leaderboard_idx
  on quiz_scores (difficulty, score desc, created_at asc);
```

### Credentials

In `config.js`:

```js
window.QUIZ_CONFIG = {
  SUPABASE_URL: 'https://YOUR_PROJECT.supabase.co',
  SUPABASE_ANON_KEY: 'YOUR_ANON_KEY',
  TABLE_NAME: 'quiz_scores',
  LEADERBOARD_LIMIT: 10,
};
```

The anon key is public — RLS protects your data, not key secrecy.

## Local preview

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy to Vercel

```bash
npx vercel --prod
```

Or import the repo on https://vercel.com/new (Framework: Other). Auto-redeploys on every git push.

## How the bank was built

Source: ~300,000 raw generator questions across L1–L6. Pipeline applied 30+ filtering rules:

- **Structural**: dropped duplicate options, empty options, malformed blanks, oversized questions
- **Format**: dropped meta-questions ("Which sentence uses X correctly?"), synonym-substitution prompts, comparative dumps, trivia patterns
- **Distractors**: dropped grammar-error distractors (`sitted`, `informations`, `do attract`), lemma overlaps, length outliers, parallel-structure mismatches
- **Stems**: enforced minimum length per level to ensure enough context (L3 ≥ 50 chars, L6 ≥ 75)
- **Vocabulary calibration**: per-level Zipf frequency bounds (L1 correct answer must be common; L6 correct answer must be rare) + per-level blocklist of known-mistagged words
- **Multi-correct heuristic**: ~180-cluster synonym dictionary; questions with 2+ options in the same cluster get dropped
- **Generic stem ban at L4+**: dropped "The X is __." patterns that don't anchor a single answer
- **Diversity**: max 3 questions per vocabulary-word cluster
- **Quality scoring within survivors**: bonuses for anchor patterns (preposition + blank, specific numbers/proper nouns), stem length sweet spot, and correct answers rarer than distractors

Each level keeps its top 2,000 by quality score.

## Known limitations

The bank cannot be fully cleaned without semantic review (LLM-as-judge or human). After all heuristic filtering:

- **L1 / L2**: ~90% genuinely at their tagged level
- **L3 / L4**: ~85%; some made-up-word distractors slip through, occasional multi-correct
- **L5 / L6**: ~70–75%; near-synonym multi-correct is the dominant remaining failure (e.g., `dynamics / energies / forces / influences` all defensibly fit "kinetic ___ that shape urban environment")

This is inherent to C1/C2 vocabulary testing — fine semantic distinctions between near-synonyms genuinely have multiple defensible answers, and only a human or judge model can pick the *best* of four.
