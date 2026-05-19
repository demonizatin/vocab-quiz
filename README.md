# Vocabulary Quiz

A timed English vocabulary quiz with difficulty levels (Easy / Medium / Hard), per-difficulty Supabase leaderboards, and a curated 15,000-question bank spanning CEFR L1–L6 (A1 → C2).

## Layout

```
vocab-quiz/
├── index.html          The game (UI + logic + leaderboard)
├── config.js           Supabase credentials
├── questions.json      15k-question pool, compact format (app runtime)
├── vercel.json         Static deploy config
├── data/               Source bank (canonical, full schema)
│   ├── level_1.json    2,500 A1 / Beginner
│   ├── level_2.json    2,500 A2 / Elementary
│   ├── level_3.json    2,500 B1 / Intermediate
│   ├── level_4.json    2,500 B2 / Upper-intermediate
│   ├── level_5.json    2,500 C1 / Advanced
│   ├── level_6.json    2,500 C2 / Proficiency
│   ├── all_levels.json 15,000 consolidated, full schema
│   └── README.md       Pipeline details + caveats
├── .gitignore
└── README.md
```

**Two formats, on purpose:**

- `data/*.json` is the canonical bank — preserves the original schema (`id`, `question`, `options_json`, `english_level`, `correct_index` as strings). Use this for any external consumer (mobile app, API, second product).
- `questions.json` at the root is a compact-keyed version (`i`, `q`, `o`, `l`, `c` with proper types) that the deployed app fetches at load time. It's derived from `data/all_levels.json`.

## Question selection per difficulty

Each 10-question game pulls exactly:

| Difficulty | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| Easy | 6 | 3 | 1 | – | – | – |
| Medium | – | 1 | 3 | 4 | 2 | – |
| Hard | – | – | 1 | 2 | 4 | 3 |

Mixes overlap by one level so each difficulty has occasional curveballs without crossing into unfair territory.

## Supabase setup

### Fresh project

In the Supabase SQL Editor:

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

### Already have the older single-difficulty table

Just run the migration:

```sql
alter table quiz_scores
  add column if not exists difficulty text
  check (difficulty in ('easy', 'medium', 'hard'));

create index if not exists quiz_scores_leaderboard_idx
  on quiz_scores (difficulty, score desc, created_at asc);
```

### Credentials

Edit `config.js`:

```js
window.QUIZ_CONFIG = {
  SUPABASE_URL: 'https://YOUR_PROJECT.supabase.co',
  SUPABASE_ANON_KEY: 'YOUR_ANON_KEY',
  TABLE_NAME: 'quiz_scores',
  LEADERBOARD_LIMIT: 10,
};
```

The anon key is meant to be public — RLS policies above are what protect your data. If you skip this step the app still runs; the leaderboard area shows a setup hint.

## Local preview

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Don't open `index.html` directly with `file://` — the page fetches `questions.json` at load and most browsers block `fetch` on file URLs.

## Deploy to Vercel

**Dashboard:** https://vercel.com/new → Import → Framework preset **Other** → Deploy. Auto-redeploys on every push.

**CLI:** `npx vercel --prod`

## Updating the questions

If you regenerate or extend the bank in `data/`, rebuild the app's runtime `questions.json` from it:

```bash
python3 -c "
import json, random
with open('data/all_levels.json') as f: bank = json.load(f)
compact = [{'i': int(r['id']), 'q': r['question'],
            'o': json.loads(r['options_json']),
            'l': int(r['english_level']),
            'c': int(r['correct_index'])} for r in bank]
random.seed(2026); random.shuffle(compact)
with open('questions.json', 'w') as f:
    json.dump(compact, f, ensure_ascii=False, separators=(',',':'))
print(f'Wrote {len(compact)} questions')
"
```

Then commit and push; Vercel redeploys.

## Caveats (about the question bank)

The bank was filter-curated from ~300k generator output using 30+ structural and CEFR-aligned rules. Quality varies slightly by level:

- **L1 / L2**: ~85–90% genuinely at their tagged level.
- **L3**: ~85%; some made-up-word distractors I couldn't auto-detect.
- **L4**: ~80%; close-synonym multi-correct still happens occasionally.
- **L5 / L6**: ~70–75%; multi-correct on near-synonyms is the dominant remaining failure mode.

See `data/README.md` for the full pipeline and what each rule does.

To get the last 10–25% would need either an LLM-as-judge run (~$30–60 to grade all 15k via a small model) or a human review pass.
