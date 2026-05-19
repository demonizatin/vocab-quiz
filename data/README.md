# Vocabulary Bank

A curated bank of 15,000 English vocabulary multiple-choice questions, organized by CEFR-aligned levels (L1 → L6, roughly A1 → C2).

## Files

| File | Rows | Description |
|------|------|-------------|
| `level_1.json` | 2,500 | A1 / Beginner |
| `level_2.json` | 2,500 | A2 / Elementary |
| `level_3.json` | 2,500 | B1 / Intermediate |
| `level_4.json` | 2,500 | B2 / Upper-intermediate |
| `level_5.json` | 2,500 | C1 / Advanced |
| `level_6.json` | 2,500 | C2 / Proficiency |
| `all_levels.json` | 15,000 | Consolidated, sorted by level then id |

## Schema

Each row is an object:

```json
{
  "id": "6001",
  "question": "The cake has a round __.",
  "options_json": "[\"colour\", \"shape\", \"taste\", \"smell\"]",
  "english_level": "1",
  "correct_index": "1"
}
```

- `id` — original generator ID, kept as a string so external references don't break
- `question` — stem with `__` blank
- `options_json` — JSON-encoded array of exactly 4 options (matches source format)
- `english_level` — string `"1"` through `"6"`
- `correct_index` — string `"0"` through `"3"`, indexes into the options array

## How this bank was built

Source: ~300,000 raw generated questions across L1–L6.

Selection pipeline (rough survival rates in parentheses):

1. **Structural filter**: drop duplicate options, empty options, malformed blanks, total-length > 150 chars. (~30% retention)
2. **Format filter**: drop meta-questions ("Which sentence uses X correctly?"), synonym-substitution prompts, comparative dumps ("more X / most X" sweeps), trivia patterns ("is the capital of"). (~70% of above)
3. **Distractor quality filter**: drop options with grammar errors (`sitted`, `informations`, `more better`), lemma overlaps, parallel-structure mismatches, length-outlier tells. (~95%)
4. **Stem specificity filter**: drop too-short or too-long stems per level. (~95%)
5. **Multi-correct filter**: ~120-cluster synonym dictionary; drop if 2+ options share a cluster. (~90%)
6. **Level calibration (Zipf frequency)**: tighter bounds per level. L1 requires correct answer Zipf ≥ 3.7; L6 has a 5.0 upper cap. (~50–70% per level)
7. **Per-level vocabulary blocklist**: hand-curated list of words that shouldn't appear at L1/L2 (e.g., `compelled`, `incapacitated`, `linger`).
8. **Diversity cap**: max 3 questions per vocabulary-word cluster (~30 IDs each); within cluster, shortest total length wins.
9. **Option order shuffled** per question, with `correct_index` rewritten — so no positional bias in the bank.

Each surviving level pool is 20,000+; the bank picks the top 2,500 with maximum vocab-word diversity.

## Known limitations

- **L5/L6 multi-correct**: ~25–30% of high-level questions have a defensible alternate answer because near-synonym distractors are an inherent vocabulary-teaching style at C1/C2.
- **Some wrong keys remain**: the filter cannot programmatically verify the marked correct answer is the *best* of four. Spot-checks suggest ~3–5% of L5/L6 keys are arguable.
- **Cultural specificity**: a small fraction of questions reference Indian-English context (Diwali, RBI, Mumbai, kabaddi, etc.). Kept because most are legitimate vocab tests; flag if your audience is non-Indian.

## License

Use freely. The underlying source data is from the project owner; this repo is the curated subset.
