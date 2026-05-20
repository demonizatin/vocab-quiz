# Vocabulary Quiz

A timed English vocabulary quiz: 10 questions, 7 seconds each, three difficulties (Easy / Medium / Hard), per-difficulty Supabase leaderboards. 8,907-question bank curated using IELTS-instructor rules including a no-specialty-knowledge filter.

## Layout

```
vocab-quiz/
├── index.html          App: UI + game logic + leaderboard
├── config.js           Supabase credentials
├── questions.json      8,907 pool, compact format (app runtime)
├── vercel.json         Static deploy config
├── data/               Source bank (canonical, full schema)
│   ├── level_1.json    1,500 A1 / Beginner
│   ├── level_2.json    1,495 A2 / Elementary
│   ├── level_3.json    1,491 B1 / Intermediate
│   ├── level_4.json    1,489 B2 / Upper-intermediate
│   ├── level_5.json    1,485 C1 / Advanced
│   ├── level_6.json    1,447 C2 / Proficiency
│   └── all_levels.json 8,907 consolidated
├── .gitignore
└── README.md
```

## Filtering rules

Six rules applied to the original 60k question pool:

1. **Well-formed** — one blank in stem, four distinct non-empty options, valid correct_index
2. **Tests vocabulary, not tricks** — drops meta-questions and trivia
3. **Real-English distractors** — no `sitted`, `informations`, `more better` style errors
4. **One best answer** — drops questions where 2+ options sit in a tight synonym cluster
5. **Vocabulary fits the level** — Zipf frequency lower bound per level + small L1/L2 blocklist of too-hard words
6. **No specialty domain knowledge** — drops questions where the correct answer or stem requires field-specific knowledge (cricket terminology, automotive parts, physics/biology/chemistry jargon, philosophy terms, niche bureaucracy)

Rule 6 is what changed in this version: questions like `'yorker'`, `'fenders'`, `'schengen visa'`, `'quantum entanglement'`, `'ontological framework'` are gone. General Indian-context vocabulary (Diwali, Bangalore, biryani) is kept — that's cultural context for the user base, not specialty knowledge.

## Difficulty mix

| Difficulty | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| Easy | 6 | 3 | 1 | – | – | – |
| Medium | – | 1 | 3 | 4 | 2 | – |
| Hard | – | – | 1 | 2 | 4 | 3 |

## Supabase setup

See previous README for SQL schema and migrations. Same `quiz_scores` table with `difficulty` column.

## What still won't be perfect

Near-synonym multi-correct at L5/L6 remains the dominant residual issue — `amalgamating / integrating / synthesizing` style. The only way to push this below ~30% is an LLM-as-judge pass on the bank.
