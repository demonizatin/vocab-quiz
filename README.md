# Vocabulary Quiz

A timed English vocabulary quiz with three difficulties (Easy / Medium / Hard), per-difficulty Supabase leaderboards, and a 9,000-question bank curated using five IELTS-instructor rules.

## Layout

```
vocab-quiz/
├── index.html          App: UI + game logic + leaderboard
├── config.js           Supabase credentials
├── questions.json      9k pool, compact format (app runtime)
├── vercel.json         Static deploy config
├── data/               Source bank (canonical, full schema)
│   ├── level_1.json    1,500 A1 / Beginner
│   ├── level_2.json    1,500 A2 / Elementary
│   ├── level_3.json    1,500 B1 / Intermediate
│   ├── level_4.json    1,500 B2 / Upper-intermediate
│   ├── level_5.json    1,500 C1 / Advanced
│   ├── level_6.json    1,500 C2 / Proficiency
│   └── all_levels.json 9,000 consolidated, full schema
├── .gitignore
└── README.md
```

## The five filtering rules

Each question must satisfy ALL of:

1. **Well-formed** — one blank in stem, four distinct non-empty options, valid correct_index, options don't themselves contain `__`, total length under 150 chars
2. **Tests vocabulary, not tricks** — drops meta-questions ("Which sentence uses X correctly?"), drops trivia ("Which is the capital of..."), drops grammar drills
3. **Real-English distractors** — no `sitted`, `informations`, `do attract`, `more better` and similar grammar-error options
4. **One best answer** — drops questions where two of the four options sit in a small hand-curated synonym cluster (~40 obvious clusters like `said/told/stated`, `amalgamate/integrate/synthesize`, `intense/vivid/forceful`)
5. **Vocabulary matches the level** — Zipf frequency lower bound per level (L1 ≥ 3.7, L6 ≥ 0.8); plus a tight blocklist of specific too-hard words for L1 and L2 (`compelled`, `incapacitated`, `linger`, `ethereal`, `agonies`, `compliance`, etc.)

That's it. No quality scoring, no anchor-pattern bonuses, no suffix heuristics — just the five rules. Original 60k question pool → 9k after filtering, 1,500 per level.

## Difficulty mix in the app

Each 10-question game pulls exactly:

| Difficulty | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| Easy | 6 | 3 | 1 | – | – | – |
| Medium | – | 1 | 3 | 4 | 2 | – |
| Hard | – | – | 1 | 2 | 4 | 3 |

## Supabase setup

Fresh project:

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

Adding `difficulty` to an existing table:

```sql
alter table quiz_scores
  add column if not exists difficulty text
  check (difficulty in ('easy', 'medium', 'hard'));

create index if not exists quiz_scores_leaderboard_idx
  on quiz_scores (difficulty, score desc, created_at asc);
```

Then edit `config.js` with your project URL and anon key.

## Local preview

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Honest quality notes

- **L1, L2, L3**: ~85-90% genuinely at the tagged level. Strong.
- **L4**: ~70% clean. Some near-synonym multi-correct (`elevate / augment / better` for "improve").
- **L5, L6**: ~50-60% clean. The dominant remaining issue is C1/C2 near-synonym distractors (`amalgamating / integrating / synthesizing`, `discerning / astute / erudite / cerebral`) — multiple options defensibly fit. This is inherent to how the source data was generated and cannot be fully filtered out by heuristics.

If you want the L5/L6 multi-correct rate dropped from ~40% to ~5%, the only realistic path is an LLM-as-judge pass on the bank — independent of this filter.
