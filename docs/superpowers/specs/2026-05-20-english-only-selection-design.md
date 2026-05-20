# v9 English-Only Question Selector — Design

**Date:** 2026-05-20
**Status:** Approved by user, implementation underway
**Supersedes:** v8 phrasal-anchored ruleset (HANDOFF.md)

## Goal

Build a new question selector that starts from the raw 300k bank and keeps only questions that test **English language ability** — vocabulary, idioms, collocation, grammar, semantics, usage. Drop anything where the answer requires non-English world knowledge (history, science, geography, philosophy trivia, named-entity facts).

User feedback: "v8 was underwhelming." This design replaces the v8 phrasal-only constraint at L4+ with a more principled world-knowledge filter.

## Scope

- Input: `data/raw/level_{1..6}.json` — 50k questions per CEFR level, 300k total.
- Output: `data/english_only/level_{1..6}.json` + `all_levels.json` + `report.txt`.
- Final integration: replace runtime `questions.json` and `data/level_N.json` with v9 output so the running app moves to v9.

## What "qualifies as English"

User decision (from brainstorming, option 3): keep anything that tests English ability — vocab/collocation cloze (Type A), idiom/phrase comprehension (Type B), meta-linguistic usage questions (Type C), cultural-context cloze (Type D). Drop world-knowledge trivia (Type E) where the answer requires knowing facts from history, science, geography, etc.

## Rule pipeline

A question is **kept** only if it passes all rules. Rules 1–6 are inherited from v8 (structural quality). Rule 7 is new (English-only). The v8 L4+ phrasal-only rule is **dropped**.

### Rule 1 — Well-formed
- Exactly one `__` blank in stem
- 4 distinct, non-empty options
- Valid `correct_index` in [0,3]
- No `__` inside options
- Total length ≤ 150 chars

### Rule 2 — Tests vocab, not tricks
- Drop meta-questions like `Which sentence uses X?`, `The word X means…`
- Drop trivia patterns like `is the capital of`, `was invented by`, `chemical formula for`
- Drop "best replacement / closest in meaning" prompts

(Note: Rule 2 overlaps partly with new Rule 7. Both kept — they're complementary.)

### Rule 3 — Real-English distractors
- Drop if any option matches a known grammar-error string (`sitted, putted, growed, informations, advices, do attract, more better`, etc., ~40 strings)

### Rule 4 — One best answer
- Drop if 2+ options sit in the same hand-curated synonym cluster (~40 tight clusters, kept small as in v8)

### Rule 5 — Vocabulary fits the level
- Per-level Zipf frequency floor on the correct answer:
  - L1: 4.0, L2: 3.5, L3: 2.7, L4: 2.2, L5: 1.5, L6: 0.8
- Per-level blocklists (L1, L2) for over-difficult words slipping in

### Rule 6 — No specialty domain knowledge (keyword-based)
- Drop if correct answer or stem contains specialty jargon: cricket, automotive, hard sciences, philosophy, bureaucracy, specialty music/cooking (~120 words)
- Preserves general Indian-context vocab (Diwali, Mumbai, RBI, biryani, monsoon, IIM, etc.)

### Rule 7 — NEW — No world-knowledge trivia (structural)

**Drop only when BOTH conditions fire in stem (or options):**

#### Condition A — Proper noun present
A capitalized mid-sentence word that is:
- Not the first word of the sentence
- Not the pronoun "I"
- Not in a whitelist of common Indian-context tokens: `Diwali, Holi, Mumbai, Delhi, Bangalore, Bengaluru, Chennai, Kolkata, Hyderabad, India, Indian, Hindi, Tamil, Marathi, Bengali, Punjabi, Gujarati, RBI, IIM, IIT, Bollywood, English, January-December, Monday-Sunday`
- Not in a common English honorific or function whitelist: `Mr, Mrs, Ms, Dr, Sir, Madam, OK, TV, USA, UK, US`

#### Condition B — Trivia framing pattern in stem
Case-insensitive substring match against:
- `is the capital of`, `is known for`, `was invented by`, `was born in`
- `is credited to`, `is credited with`, `credited as`
- `in historical texts`, `in ancient`, `in classical`
- `discovered`, `authored`, `wrote`, `composed`, `coined`, `founded by`, `named after`
- `first to`, `best known for`, `famous for`, `renowned for`
- `refers to` (only counts as trivia framing when a proper noun is also present, hence the AND)

**Result:** "My guru says meditation __" survives (no proper noun + no trivia frame). "Chomsky's Syntactic Structures __ linguistics" drops (Chomsky proper noun + "credited to"-equivalent verb).

### Transformation — Option shuffling
Each surviving question has options reordered (Fisher-Yates, seeded for determinism) and `correct_index` rewritten. Eliminates positional bias.

## v8 Rule 7 (phrasal-only at L4+) — explicitly DROPPED

The v8 phrasal-only constraint at L4+ was a structural workaround for the L4-L6 multi-correct problem. It shrank the bank to 6.7k but felt over-pruned. Removing it should roughly double L4-L6 yield. Multi-correct issues are partly mitigated by Rules 4 (synonym soup) and the new Rule 7 (trivia framing).

## Expected output volume

| Level | v8 count | Estimated v9 count |
|-------|----------|---------------------|
| L1 | 1,500 | 1,500–2,500 |
| L2 | 1,500 | 1,500–2,500 |
| L3 | 1,500 | 1,500–2,500 |
| L4 | 800 | 2,000–3,500 |
| L5 | 800 | 2,000–3,500 |
| L6 | 600 | 1,500–3,000 |
| **Total** | **6,700** | **~10–17k** |

If yield falls dramatically outside this band, the run is flagged before declaring done.

## Output files

```
data/english_only/
├── level_1.json … level_6.json    # canonical schema (id, question, options_json, english_level, correct_index)
├── all_levels.json                  # consolidated
└── report.txt                        # drop counts per rule, per level
```

Plus:
- `scripts/select_english_only.py` — reproducible pipeline
- After validation, the runtime `questions.json` and `data/level_{1..6}.json` are replaced with v9 output. The old v8 banks are overwritten — git history is the rollback path.

## Schema

- `data/english_only/level_N.json` uses the **canonical source schema**: `id` (string), `question` (string), `options_json` (stringified JSON array), `english_level` (string), `correct_index` (string).
- The runtime `questions.json` uses the **compact app schema**: `i` (int id), `q` (question), `o` (options array, not stringified), `l` (int level), `c` (int correct_index).

## What this does NOT change

- `index.html`, `config.js`, Supabase schema, leaderboard logic — untouched.
- `data/raw/level_N.json` — the 300k Browse-view source is untouched.
- Difficulty mix (`DIFF_MIX` in `index.html`) — unchanged.

## Constraints honored

- No LLM-as-judge (user explicitly forbids).
- No "quality scoring" composite (v4 lesson).
- Single-script pipeline, deterministic, reproducible.
