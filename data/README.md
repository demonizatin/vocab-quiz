# Question Bank

12,000 English vocabulary multiple-choice questions, 2,000 per CEFR level (L1 → L6, roughly A1 → C2).

## Files

| File | Rows | Level |
|------|------|-------|
| `level_1.json` | 2,000 | A1 / Beginner |
| `level_2.json` | 2,000 | A2 / Elementary |
| `level_3.json` | 2,000 | B1 / Intermediate |
| `level_4.json` | 2,000 | B2 / Upper-intermediate |
| `level_5.json` | 2,000 | C1 / Advanced |
| `level_6.json` | 2,000 | C2 / Proficiency |
| `all_levels.json` | 12,000 | All, sorted by level then id |

## Schema

```json
{
  "id": "6001",
  "question": "The cake has a round __.",
  "options_json": "[\"colour\", \"shape\", \"taste\", \"smell\"]",
  "english_level": "1",
  "correct_index": "1"
}
```

All values are strings (matches source format). `options_json` is a JSON-encoded array of exactly 4 options. Option order is shuffled per question and `correct_index` is rewritten — so there's no positional bias.

## Vocabulary coverage

Each level has 2,000 distinct vocabulary words — no word is tested more than once within a level.

## Caveats

After heuristic filtering, ~75–90% of questions per level are at their tagged level with an unambiguous correct answer. The remaining 10–25% (concentrated in L5–L6) have residual issues that require semantic review to fully resolve. See the root README for the full quality breakdown.
