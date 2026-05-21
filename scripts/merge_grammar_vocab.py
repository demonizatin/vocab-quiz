"""
Merge grammar questions into the runtime pool.

Reads:
  data/english_only/all_levels.json    (24,000 v9 vocab questions)
  /Users/priyansh/Downloads/query_result_2026-05-20T21_17_32.576794588+05_30.csv
                                       (11,021 grammar questions from prod DB)

Writes:
  questions.json                       (combined compact pool: vocab + grammar)
  data/grammar_bank_v1.json            (canonical grammar bank, for reference)

Compact schema (used by the app):
  { i: number, q: string, o: string[4], l: 1-6, c: 0-3, t: 'v' | 'g' }

ID ranges (no collision):
  vocab:   6,000 – 331,648 (from raw bank IDs, preserved)
  grammar: 1,000,001 – 1,047,824 (raw grammar id + 1,000,000 offset)
"""

import csv
import json
import random
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VOCAB_SRC = REPO / "data" / "english_only" / "all_levels.json"
GRAMMAR_CSV = Path("/Users/priyansh/Downloads/query_result_2026-05-20T21_17_32.576794588+05_30.csv")
RUNTIME_OUT = REPO / "questions.json"
GRAMMAR_OUT = REPO / "data" / "grammar_bank_v1.json"

GRAMMAR_ID_OFFSET = 1_000_000
SHUFFLE_SEED = 20260520

# Reading-speed cap per level. A question whose (stem + 4 options) total
# character count exceeds the cap for its level is DROPPED — it eats too
# much of the 7-second budget for a player at that tier. L6 keeps a
# generous cap (top tier reads fastest).
CHAR_CAP = {1: 80, 2: 110, 3: 140, 4: 180, 5: 220, 6: 280}


def total_chars(q: dict) -> int:
    return len(q["q"]) + sum(len(o) for o in q["o"])


def normalize_blank(q: str) -> str:
    """Match vocab format: collapse 2+ underscores to '__'."""
    return re.sub(r"_{2,}", "__", q)


def load_vocab() -> list[dict]:
    rows = json.loads(VOCAB_SRC.read_text())
    out = []
    for r in rows:
        opts = json.loads(r["options_json"])
        out.append({
            "i": int(r["id"]),
            "q": r["question"],
            "o": opts,
            "l": int(r["english_level"]),
            "c": int(r["correct_index"]),
            "t": "v",
        })
    return out


def load_grammar() -> list[dict]:
    out = []
    with GRAMMAR_CSV.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            payload = json.loads(row["payload"])
            opts = list(payload["options"])
            if len(opts) != 4:
                continue
            ci = int(payload["answerIndex"])
            if not (0 <= ci < 4):
                continue
            stem = normalize_blank(payload["question"])
            if "__" not in stem:
                # MCQ-style (no blank) — keep, like Type B/C in vocab
                pass
            out.append({
                "i": int(row["id"]) + GRAMMAR_ID_OFFSET,
                "q": stem,
                "o": opts,
                "l": int(row["english_level"]),
                "c": ci,
                "t": "g",
            })
    return out


def write_grammar_canonical(rows: list[dict]) -> None:
    """Also save grammar in canonical schema for inspection / re-ingest."""
    canonical = [
        {
            "id": str(r["i"] - GRAMMAR_ID_OFFSET),
            "question": r["q"],
            "options_json": json.dumps(r["o"], ensure_ascii=False),
            "english_level": str(r["l"]),
            "correct_index": str(r["c"]),
        }
        for r in rows
    ]
    GRAMMAR_OUT.write_text(json.dumps(canonical, ensure_ascii=False, indent=2))


def filter_by_char_cap(rows: list[dict]) -> tuple[list[dict], dict]:
    """Drop questions whose (stem + options) total chars exceed the per-level cap."""
    from collections import Counter
    kept, dropped = [], Counter()
    for r in rows:
        cap = CHAR_CAP.get(r["l"])
        if cap is None or total_chars(r) <= cap:
            kept.append(r)
        else:
            dropped[(r["t"], r["l"])] += 1
    return kept, dict(dropped)


def main() -> None:
    vocab = load_vocab()
    grammar = load_grammar()
    print(f"vocab loaded: {len(vocab):,}")
    print(f"grammar loaded: {len(grammar):,}")

    vocab_filtered, vocab_dropped = filter_by_char_cap(vocab)
    grammar_filtered, grammar_dropped = filter_by_char_cap(grammar)
    print(f"\nDropped over char-cap (vocab): {sum(vocab_dropped.values()):,}")
    for (t, lv), c in sorted(vocab_dropped.items()):
        print(f"  {t} L{lv}: {c:,}")
    print(f"Dropped over char-cap (grammar): {sum(grammar_dropped.values()):,}")
    for (t, lv), c in sorted(grammar_dropped.items()):
        print(f"  {t} L{lv}: {c:,}")
    print(f"\nvocab after cap: {len(vocab_filtered):,}")
    print(f"grammar after cap: {len(grammar_filtered):,}")

    write_grammar_canonical(grammar_filtered)
    print(f"wrote canonical grammar -> {GRAMMAR_OUT}")

    combined = vocab_filtered + grammar_filtered
    # ID collision check
    ids = [r["i"] for r in combined]
    if len(set(ids)) != len(ids):
        raise RuntimeError("ID collision after merge")

    # Shuffle once so the bank isn't in lexicographic order
    rng = random.Random(SHUFFLE_SEED)
    rng.shuffle(combined)

    with RUNTIME_OUT.open("w") as f:
        json.dump(combined, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote runtime pool -> {RUNTIME_OUT} ({RUNTIME_OUT.stat().st_size:,} bytes)")

    # Per-(type, level) summary
    from collections import Counter
    counts = Counter((r["t"], r["l"]) for r in combined)
    print("\nFinal pool by (type, level):")
    for t in ("v", "g"):
        for lv in range(1, 7):
            c = counts.get((t, lv), 0)
            if c:
                print(f"  {t} L{lv}: {c:,}")


if __name__ == "__main__":
    main()
