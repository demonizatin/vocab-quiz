# Question Bank

9,000 English vocabulary multiple-choice questions, 1,500 per CEFR level (L1 → L6, roughly A1 → C2). Source: original 60k generated pool. Curated using five IELTS-instructor rules — see root README.

## Files

| File | Rows | Level |
|------|------|-------|
| `level_1.json` | 1,500 | A1 / Beginner |
| `level_2.json` | 1,500 | A2 / Elementary |
| `level_3.json` | 1,500 | B1 / Intermediate |
| `level_4.json` | 1,500 | B2 / Upper-intermediate |
| `level_5.json` | 1,500 | C1 / Advanced |
| `level_6.json` | 1,500 | C2 / Proficiency |
| `all_levels.json` | 9,000 | All, sorted by level then id |

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

All values as strings. `options_json` is a JSON-encoded array of exactly 4 options. Option order is shuffled per question, `correct_index` rewritten to match — no positional bias.
