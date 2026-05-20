"""
Builds the vocab-portion ELO ladder sheets:
  - vocab_ladder_v9.csv         : ladder spec (one row per ELO band)
  - vocab_bank_v9_typed.csv     : the 24k bank with question_type and merged L5/L6

Companion to scripts/select_english_only.py. Reads the v9 bank from
data/english_only/all_levels.json. L6 questions are reclassified as L5
(grammar ceiling is C1 / L5).

Output is written to:
  data/english_only/vocab_ladder_v9.csv
  data/english_only/vocab_bank_v9_typed.csv

The Desktop copies are made by the caller (Bash cp).

Notes:
- Each quiz = 10 questions = grammar + vocab
- Grammar uses the user's existing CEFR A1-C1 ladder (not regenerated here)
- Vocab portion increases with ELO (2 -> 8) and cloze share rises with ELO
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "data" / "english_only" / "all_levels.json"
LADDER_OUT = REPO_ROOT / "data" / "english_only" / "vocab_ladder_v9.csv"
BANK_OUT = REPO_ROOT / "data" / "english_only" / "vocab_bank_v9_typed.csv"

BLANK_RE = re.compile(r"__+")

LADDER = [
    # (band_label, min_elo, max_elo, grammar_count, vocab_count, L1, L2, L3, L4, L5, cloze_quota, meta_quota)
    ("<775",        0,     774,  8, 2, 2, 0, 0, 0, 0, 2, 0),
    ("775-924",   775,     924,  7, 3, 2, 1, 0, 0, 0, 3, 0),
    ("925-1074",  925,    1074,  6, 4, 1, 2, 1, 0, 0, 3, 1),
    ("1075-1224", 1075,   1224,  5, 5, 1, 2, 2, 0, 0, 4, 1),
    ("1225-1399", 1225,   1399,  4, 6, 0, 1, 2, 2, 1, 5, 1),
    ("1400-1499", 1400,   1499,  3, 7, 0, 1, 2, 2, 2, 6, 1),
    ("1500+",     1500, 99999,  2, 8, 0, 1, 1, 3, 3, 8, 0),
]


def write_ladder() -> None:
    fields = [
        "band_label", "min_elo", "max_elo",
        "grammar_count", "vocab_count",
        "vocab_L1", "vocab_L2", "vocab_L3", "vocab_L4", "vocab_L5",
        "cloze_quota", "meta_quota",
    ]
    with LADDER_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(fields)
        for row in LADDER:
            w.writerow(row)


def eligible_bands(level: int, qtype: str) -> str:
    """For each ELO band, the question is eligible if:
        - the band's count for this vocab_level > 0, AND
        - the question type fits (a band with meta_quota=0 only takes cloze)."""
    bands = []
    for row in LADDER:
        (band, _min, _max, _g, _v, l1, l2, l3, l4, l5, cloze_q, meta_q) = row
        level_counts = [l1, l2, l3, l4, l5]
        if level_counts[level - 1] == 0:
            continue
        if qtype == "meta" and meta_q == 0:
            continue
        bands.append(band)
    return ",".join(bands)


def write_bank() -> None:
    rows = json.loads(SRC.read_text())
    fields = [
        "id", "question", "options_json", "english_level",
        "correct_index", "question_type", "eligible_elo_bands",
    ]
    with BANK_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            native_level = int(r["english_level"])
            # native_level is preserved (1-6). For eligibility lookup only,
            # we treat L6 as L5 since the app maps L6 -> L5 at quiz time.
            effective_level = 5 if native_level == 6 else native_level
            qtype = "cloze" if BLANK_RE.search(r["question"]) else "meta"
            w.writerow({
                "id": r["id"],
                "question": r["question"],
                "options_json": r["options_json"],
                "english_level": str(native_level),
                "correct_index": r["correct_index"],
                "question_type": qtype,
                "eligible_elo_bands": eligible_bands(effective_level, qtype),
            })


def main() -> None:
    write_ladder()
    write_bank()
    # quick stats
    rows = json.loads(SRC.read_text())
    level_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    type_counts = {"cloze": 0, "meta": 0}
    for r in rows:
        lvl = int(r["english_level"])
        level_counts[lvl] += 1
        type_counts["cloze" if BLANK_RE.search(r["question"]) else "meta"] += 1
    print(f"ladder spec -> {LADDER_OUT}")
    print(f"typed bank  -> {BANK_OUT}")
    print(f"bank rows: {len(rows)}  | native level counts: {level_counts}")
    print(f"types: {type_counts}")
    print("L6 questions inherit L5's eligible_elo_bands (app maps L6->L5 at quiz time).")


if __name__ == "__main__":
    main()
