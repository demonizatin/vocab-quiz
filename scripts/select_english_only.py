"""
v9 English-Only Question Selector

Reads raw 300k-question bank from data/raw/level_{1..6}.json (compact schema).
Applies v8 Rules 1-6 (structural quality, inherited) plus new Rule 7
(world-knowledge filter: drops trivia when proper noun + trivia framing co-occur).

Outputs:
  data/english_only/level_{1..6}.json   (canonical schema, per-level)
  data/english_only/all_levels.json     (canonical schema, consolidated)
  data/english_only/report.txt          (drop counts per rule, per level)

Run from repo root:
    python3 scripts/select_english_only.py
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from wordfreq import zipf_frequency

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_DIR = REPO_ROOT / "data" / "english_only"

SHUFFLE_SEED = 20260520  # determinism
PER_LEVEL_CAP = 4000  # max kept questions per level (deterministic sample if exceeded)

# ---------- Rule 1: well-formed ----------
MAX_LEN = 150
BLANK_RE = re.compile(r"__+")


def rule1_well_formed(q: str, opts: list[str], ci: int) -> str | None:
    if not (0 <= ci < 4):
        return "1_bad_ci"
    if len(opts) != 4:
        return "1_not_4_opts"
    if any((not o) or (not o.strip()) for o in opts):
        return "1_empty_opt"
    if len(set(o.strip().lower() for o in opts)) < 4:
        return "1_duplicate_opt"
    if any("__" in o for o in opts):
        return "1_blank_in_opt"
    # allow 0 blanks (meta-question) OR exactly 1 (cloze); 2+ is broken
    if len(BLANK_RE.findall(q)) > 1:
        return "1_too_many_blanks"
    # length budget is wider for meta-questions (sentence-length options)
    budget = 280 if len(BLANK_RE.findall(q)) == 0 else MAX_LEN
    if len(q) + sum(len(o) for o in opts) > budget:
        return "1_too_long"
    return None


def is_cloze(q: str) -> bool:
    return len(BLANK_RE.findall(q)) == 1


# ---------- Rule 2: no meta / tricks ----------
# v9: only drop genuine multi-correct tricks. Types B ("what does X mean")
# and C ("in which sentence is X used to mean Y") are KEPT.
META_PATTERNS = [
    re.compile(r"\bbest (replacement|synonym|substitute|fit|alternative)\b", re.I),
    re.compile(r"\bclosest (in meaning|to|synonym)\b", re.I),
    re.compile(r"\bmost (similar|closest|appropriate|likely synonym)\b", re.I),
]

TRIVIA_PATTERNS_R2 = [
    re.compile(r"\bchemical formula for\b", re.I),
    re.compile(r"\bcapital of\b", re.I),
    re.compile(r"\bwas invented by\b", re.I),
    re.compile(r"\bwas born in\b", re.I),
    re.compile(r"\b(speed of light|boiling point|melting point)\b", re.I),
]


def rule2_no_meta(q: str) -> str | None:
    for p in META_PATTERNS:
        if p.search(q):
            return "2_meta"
    for p in TRIVIA_PATTERNS_R2:
        if p.search(q):
            return "2_trivia"
    return None


# ---------- Rule 3: no grammar-error distractors ----------
GRAMMAR_ERRORS = {
    "sitted", "putted", "growed", "comed", "goed", "thinked", "bringed",
    "buyed", "catched", "drinked", "eated", "feeled", "finded", "flied",
    "knowed", "maked", "runned", "selled", "speaked", "spended", "teached",
    "telled", "throwed", "winned", "writed",
    "informations", "advices", "furnitures", "equipments", "luggages",
    "softwares", "researches", "feedbacks",
    "do attract", "do happen", "did went", "did saw",
    "more better", "most best", "more older", "more bigger",
    "more worse", "most worst",
    "childs", "mans", "womans", "foots", "tooths", "mouses",
    "more easier", "more harder",
    "amn't", "ain't going",
}


def rule3_real_distractors(opts: list[str]) -> str | None:
    for o in opts:
        if o.strip().lower() in GRAMMAR_ERRORS:
            return "3_grammar_error_distractor"
    return None


# ---------- Rule 4: one best answer ----------
SYNONYM_CLUSTERS = [
    {"said", "told", "stated", "uttered", "spoke"},
    {"big", "large", "huge", "enormous", "vast"},
    {"small", "tiny", "little", "minute"},
    {"happy", "joyful", "glad", "pleased", "delighted"},
    {"sad", "unhappy", "miserable", "sorrowful", "gloomy"},
    {"fast", "quick", "rapid", "swift", "speedy"},
    {"slow", "sluggish", "leisurely"},
    {"strong", "powerful", "mighty", "robust"},
    {"weak", "feeble", "frail"},
    {"smart", "clever", "intelligent", "bright", "brainy"},
    {"stupid", "foolish", "dumb", "silly"},
    {"beautiful", "pretty", "lovely", "gorgeous", "stunning"},
    {"ugly", "hideous", "unattractive"},
    {"angry", "furious", "irate", "mad", "enraged"},
    {"scared", "afraid", "frightened", "terrified"},
    {"start", "begin", "commence", "initiate"},
    {"end", "finish", "conclude", "terminate"},
    {"help", "assist", "aid", "support"},
    {"make", "create", "produce", "construct", "build"},
    {"break", "shatter", "smash", "crack"},
    {"intense", "vivid", "forceful", "powerful", "strong"},
    {"amalgamate", "integrate", "synthesize", "merge", "combine", "fuse"},
    {"reluctantly", "hesitantly", "cautiously", "tentatively"},
    {"gradually", "slowly", "progressively", "steadily"},
    {"resilient", "adaptable", "malleable", "flexible", "receptive"},
    {"recalibrates", "reorients", "rejuvenates", "refreshes", "renews"},
    {"erodes", "dissolves", "evaporates", "vanishes"},
    {"revolutionized", "reoriented", "reconceptualized", "reinvigorated", "transformed"},
    {"dashed", "foundered", "wrecked", "broken", "shattered"},
    {"hard-fought", "overwhelming", "decisive"},
    {"fatality", "victim", "sufferer", "loss", "casualty"},
    {"important", "crucial", "vital", "essential", "key", "significant"},
    {"old", "ancient", "aged", "elderly"},
    {"new", "fresh", "recent", "novel"},
    {"easy", "simple", "effortless", "straightforward"},
    {"hard", "difficult", "tough", "challenging"},
    {"good", "great", "excellent", "fine", "wonderful"},
    {"bad", "awful", "terrible", "horrible", "dreadful"},
    {"reduce", "decrease", "diminish", "lessen", "lower"},
    {"increase", "raise", "grow", "expand", "enlarge"},
]


def rule4_one_best(opts: list[str]) -> str | None:
    lows = [o.strip().lower() for o in opts]
    for cluster in SYNONYM_CLUSTERS:
        hits = sum(1 for o in lows if o in cluster)
        if hits >= 2:
            return "4_synonym_collision"
    return None


# ---------- Rule 5: vocabulary fits the level ----------
ZIPF_MIN = {1: 4.0, 2: 3.5, 3: 2.7, 4: 2.2, 5: 1.5, 6: 0.8}

LEVEL_BLOCK = {
    1: {
        "compelled", "incapacitated", "linger", "ethereal", "agonies",
        "compliance", "prosperity", "milestone", "critically", "effectively",
        "desires", "emerged", "components", "varied", "role-play",
        "comprehended", "wielded", "intricate", "perceived", "constituent",
        "subsequent", "preliminary", "comparatively",
    },
    2: {
        "exegesis", "perspicacious", "obfuscate", "ubiquitous", "esoteric",
        "lugubrious", "magnanimous", "epistemic", "ethereal",
        "promulgated", "transmogrified", "antediluvian", "sesquipedalian",
    },
}


def normalize(s: str) -> str:
    return s.strip().lower()


def rule5_fits_level(correct: str, level: int) -> str | None:
    # skip Zipf check for long answers (Type B/C have sentence-length answers)
    token_count = len(correct.split())
    if token_count > 4:
        # only enforce blocklist for long answers
        if level in LEVEL_BLOCK and normalize(correct) in LEVEL_BLOCK[level]:
            return "5_blocklist"
        return None
    z = zipf_frequency(normalize(correct), "en")
    # for short phrases, also try last token
    if z == 0 and " " in correct:
        last = correct.split()[-1]
        z = zipf_frequency(normalize(last), "en")
    if z > 0 and z < ZIPF_MIN[level]:
        return "5_too_rare"
    if level in LEVEL_BLOCK and normalize(correct) in LEVEL_BLOCK[level]:
        return "5_blocklist"
    return None


# ---------- Rule 6: no specialty domain ----------
SPECIALTY_WORDS = {
    # cricket / Indian sports
    "yorker", "bowler", "batsman", "wicket", "googly", "boundary",
    "kabaddi", "leg-spin", "off-spin", "lbw",
    # automotive
    "fender", "gasket", "carburetor", "alternator", "transmission",
    "differential", "crankshaft", "camshaft", "manifold", "spark-plug",
    # hard sciences
    "photosynthesis", "mitosis", "meiosis", "quantum", "titrate",
    "isotope", "valence", "covalent", "ionic-bond", "ribosome",
    "mitochondria", "nucleotide", "polymerase", "amino-acid",
    "tectonic", "magma", "sedimentary", "igneous", "metamorphic",
    "stratosphere", "thermosphere", "exosphere",
    # philosophy
    "epistemic", "deontological", "ontological", "phenomenology",
    "teleological", "axiology", "hermeneutic", "syllogism",
    "metaphysical", "existential",
    # bureaucracy / legal
    "schengen", "laissez-passer", "habeas", "amicus", "obiter",
    "tort", "novation", "estoppel",
    # specialty music / arts
    "fugue", "arpeggio", "leitmotif", "sonata-form", "atonal",
    "diatonic", "polyphony", "ostinato",
    # specialty cooking / chemistry
    "molecular-gastronomy", "spherification", "emulsification",
    "denature", "maillard", "deglaze",
    # specialty linguistics / etc.
    "morpheme", "phoneme", "allophone", "diphthong", "fricative",
    "plosive", "sibilant", "labiodental",
    # Latin / classical
    "unguentaria", "amphora", "stylus", "carpe-diem",
}


def rule6_no_specialty(correct: str, q: str) -> str | None:
    text = (q + " " + correct).lower()
    for w in SPECIALTY_WORDS:
        # word-boundary match; hyphens treated as separators
        pat = r"\b" + re.escape(w) + r"\b"
        if re.search(pat, text):
            return "6_specialty"
    return None


# ---------- Rule 7: NEW — no world-knowledge trivia ----------
INDIAN_CONTEXT_WHITELIST = {
    "diwali", "holi", "dussehra", "navratri", "raksha", "rakhi", "onam",
    "pongal", "ganesh", "shivratri", "janmashtami", "eid", "christmas",
    "ramzan", "ramadan", "lohri", "baisakhi",
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "kolkata",
    "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "kerala",
    "tamil", "telugu", "marathi", "gujarati", "bengali", "punjabi",
    "hindi", "kannada", "malayalam",
    "india", "indian", "bharat",
    "rbi", "iim", "iit", "isro", "bollywood", "tollywood",
    "biryani", "samosa", "chai", "lassi", "paneer", "naan", "roti",
    "monsoon", "ganga", "yamuna", "himalayas",
}
COMMON_NOUN_WHITELIST = {
    "i", "ok", "tv", "usa", "uk", "us", "mr", "mrs", "ms", "dr", "sir",
    "madam", "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "english", "spanish", "french", "german", "chinese", "japanese",
}

TRIVIA_FRAMING_PATTERNS = [
    re.compile(r"\bis the capital of\b", re.I),
    re.compile(r"\bis the largest\b", re.I),
    re.compile(r"\bis the highest\b", re.I),
    re.compile(r"\bis known for\b", re.I),
    re.compile(r"\bis famous for\b", re.I),
    re.compile(r"\bis renowned for\b", re.I),
    re.compile(r"\b(is )?best known for\b", re.I),
    re.compile(r"\bwas invented by\b", re.I),
    re.compile(r"\bwas born in\b", re.I),
    re.compile(r"\bwas founded in\b", re.I),
    re.compile(r"\bis credited (to|with|as)\b", re.I),
    re.compile(r"\bcredited (to|with|as)\b", re.I),
    re.compile(r"\bnamed after\b", re.I),
    re.compile(r"\b(founded|composed|designed|authored|written|discovered|painted|sculpted|directed) by\b", re.I),
    re.compile(r"\bin historical texts\b", re.I),
    re.compile(r"\bin ancient (rome|greece|egypt|china|persia|babylon|mesopotamia)", re.I),
    re.compile(r"\bin classical (rome|greece|antiquity|literature|texts)", re.I),
    re.compile(r"\b(refers to|refer to) ", re.I),  # only counts when proper noun also present
    re.compile(r"\bis a (book|novel|poem|play|symphony|painting|sculpture|essay|treatise) by\b", re.I),
    re.compile(r"\bin the works of\b", re.I),
    re.compile(r"\baccording to (the )?(theory|philosophy|teachings|writings|works|doctrine) of\b", re.I),
    re.compile(r"\b's (theory|philosophy|teachings|writings|works|book|novel|symphony|treatise|doctrine|paradigm|concept|principle|law|hypothesis)\b", re.I),
    re.compile(r"\btheory of (evolution|relativity|gravity|natural selection|forms|knowledge|justice|everything|general relativity|special relativity|games)\b", re.I),
    re.compile(r"\bconcept of (the )?(self|soul|being|substance|form|justice|good|truth|beauty|virtue|moderation|categorical imperative)\b", re.I),
    re.compile(r"\bin a philosophical context\b", re.I),
    re.compile(r"\bestablished the (first|earliest)\b", re.I),
    re.compile(r"\bsince (Darwin|Newton|Einstein|Aristotle|Plato|Kant|Hegel|Marx|Freud|Chomsky)\b", re.I),
    re.compile(r"\bancient (greek|roman|egyptian|chinese|persian|babylonian) (medicine|philosophy|science|mathematics|astronomy|literature|art|architecture|culture|civilization)\b", re.I),
    re.compile(r"\b(mughal|roman|greek|byzantine|ottoman|british|persian|babylonian) (court|administration|emperors?|reign|dynasty|conquest)\b", re.I),
    re.compile(r"\b(einstein|newton|darwin|aristotle|plato|kant|chomsky|marx|freud|hegel|nietzsche|shakespeare|aquinas|hume|locke|hobbes|descartes|spinoza|heidegger|schopenhauer|wittgenstein)'s\b", re.I),
    re.compile(r"\bthe foundational works of\b", re.I),
    re.compile(r"\b(shakespeare|chaucer|homer|virgil|dante|milton|austen|dickens|tolstoy|dostoevsky)\b", re.I),
    # historical / civilizational trivia framing (added after L6 leak audit)
    re.compile(r"\bthe (decline|fall|rise|origin|history|era|period|conquest|legacy) of\b", re.I),
    re.compile(r"\bgreco-(roman|latin)\b", re.I),
    re.compile(r"\b(roman|greek|egyptian|persian|mughal|british|babylonian|latin|byzantine|ottoman) (empire|civilization|civilisation|culture|antiquity|history|era|period|literature|art|sculpture|architecture|texts?|writings|mythology|gods?)\b", re.I),
    re.compile(r"\bthe (term|phrase|expression) ['\"`].+?['\"`]\s+(was|is|refers|originated|comes from)\b", re.I),
    re.compile(r"\bthe (revolution|war|battle|treaty|act|movement) of\b", re.I),
    # academic-field framing
    re.compile(r"\bin which (academic )?(field|discipline|subject|sector|industry|domain)\b", re.I),
    re.compile(r"\bis a (specific )?subfield of\b", re.I),
    re.compile(r"\bin which (academic )?field would\b", re.I),
]

PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]+(?:[-'][A-Za-z]+)*)\b")
# Common English nouns/verbs/adjectives that often appear capitalized inside
# quotes ('Folklore', 'Brand') without being proper nouns. Used to suppress
# false-positive Rule 7 trips when the only capitalized non-whitelisted token
# is a single-quoted common word.
COMMON_QUOTED_WORDS = {
    "folklore", "brand", "brands", "many", "most", "some", "few", "all",
    "any", "every", "no", "nothing", "everything", "someone", "anyone",
    "love", "hate", "joy", "fear", "anger", "trust", "hope",
    "good", "bad", "best", "worst", "great", "small", "big", "old", "new",
    "true", "false", "real", "fake", "right", "wrong",
    "fast", "slow", "happy", "sad", "rich", "poor", "young",
    "carried", "given", "taken", "made", "done", "said", "told",
    "running", "walking", "talking", "speaking", "writing",
}
# Common English words that appear capitalized at sentence start without
# being proper nouns. Anything not on this list AND capitalized at position 0
# IS a proper noun (e.g., "Einstein", "Chomsky", "Rome").
SENTENCE_STARTER_WHITELIST = {
    # pronouns
    "i", "she", "he", "it", "we", "you", "they",
    # determiners / quantifiers
    "the", "a", "an", "my", "our", "your", "their", "his", "her", "its",
    "this", "that", "these", "those", "some", "most", "many", "much",
    "every", "any", "all", "no", "both", "each", "either", "neither",
    "such", "few", "several", "another", "other",
    # prepositions
    "in", "on", "at", "of", "for", "by", "with", "from", "to", "about",
    "before", "after", "during", "while", "within", "without", "through",
    "over", "under", "above", "below", "between", "among", "across",
    "against", "around", "behind", "beyond", "into", "onto", "upon",
    "despite",
    # wh-words / conjunctions
    "when", "where", "why", "how", "which", "what", "who", "whom", "whose",
    "if", "unless", "until", "since", "because", "although", "even",
    "though", "yet", "but", "and", "or", "so", "as", "whether", "while",
    # adverbs
    "never", "always", "often", "sometimes", "usually", "today",
    "tomorrow", "yesterday", "now", "then", "here", "there", "perhaps",
    "rather", "still", "already", "yet", "soon", "later", "instead",
    "indeed", "however", "therefore", "moreover", "furthermore",
    "nevertheless", "nonetheless", "meanwhile", "afterward",
    # verbs / imperatives
    "be", "do", "have", "make", "take", "go", "come", "give", "get",
    "let", "try", "stop", "start", "keep", "use", "see", "look", "find",
    "think", "feel", "tell", "ask", "show", "say", "speak", "talk",
    # negation / contraction
    "not", "don't", "doesn't", "didn't", "won't", "can't", "couldn't",
    "shouldn't", "wouldn't", "isn't", "aren't", "wasn't", "weren't",
    "hasn't", "haven't", "hadn't",
    # modals / aux
    "can", "could", "may", "might", "must", "shall", "should", "will",
    "would", "is", "are", "was", "were", "am", "been", "being",
    "has", "had", "does", "did",
    # commonly-stem-leading
    "after", "before", "during", "by", "in", "on", "after", "to",
    "even", "only", "just", "also", "thus", "hence", "rather",
    # "Many" / "Most" already in determiners; explicit again:
    "people", "everyone", "nobody", "somebody", "anybody",
}


def _is_common_capitalized(word_lower: str) -> bool:
    """True if this lowercased word is a common English token that often
    appears capitalized for non-proper-noun reasons (sentence start, quote
    start, title, etc.)."""
    return (
        word_lower in INDIAN_CONTEXT_WHITELIST
        or word_lower in COMMON_NOUN_WHITELIST
        or word_lower in COMMON_QUOTED_WORDS
        or word_lower in SENTENCE_STARTER_WHITELIST
    )


def has_proper_noun(text: str, skip_first_capitalized: bool = False) -> tuple[bool, str | None]:
    """Return (True, word) if a capitalized non-whitelisted word exists.
    When skip_first_capitalized=True (used for options), the very first
    capitalized match is treated as a sentence-start convention and ignored.
    This prevents Type C option sentences ('Plates are scales.', 'Hitherto...')
    from being mistaken for proper-noun trivia."""
    first_skipped = False
    for m in PROPER_NOUN_RE.finditer(text):
        word = m.group(1)
        wl = word.lower()
        if skip_first_capitalized and not first_skipped:
            first_skipped = True
            # only skip if it's in the starter whitelist OR is just the
            # orthographic first word of the option; for safety, only skip
            # when the match starts at index 0 (truly first position)
            if m.start() == 0:
                continue
        if _is_common_capitalized(wl):
            continue
        return True, word
    return False, None


def count_proper_nouns(text: str, skip_first_capitalized: bool = False) -> int:
    found = set()
    first_skipped = False
    for m in PROPER_NOUN_RE.finditer(text):
        word = m.group(1)
        wl = word.lower()
        if skip_first_capitalized and not first_skipped:
            first_skipped = True
            if m.start() == 0:
                continue
        if _is_common_capitalized(wl):
            continue
        found.add(wl)
    return len(found)


_APOSTROPHES_RE = re.compile(r"['’ʼ‘]")


def _normalize_apostrophes(s: str) -> str:
    return _APOSTROPHES_RE.sub("'", s)


def has_trivia_framing(text: str) -> bool:
    text = _normalize_apostrophes(text)
    for p in TRIVIA_FRAMING_PATTERNS:
        if p.search(text):
            return True
    return False


def rule7_no_world_knowledge(q: str, opts: list[str]) -> str | None:
    q_norm = _normalize_apostrophes(q)
    opts_norm = [_normalize_apostrophes(o) for o in opts]
    # 1) multiple distinct proper nouns in stem -> trivia
    if count_proper_nouns(q_norm) >= 2:
        return "7_multi_proper_in_stem"
    # 2) proper noun anywhere + trivia framing in stem
    proper_in_any = has_proper_noun(q_norm)[0] or any(
        has_proper_noun(o, skip_first_capitalized=True)[0] for o in opts_norm
    )
    if not proper_in_any:
        return None
    if has_trivia_framing(q_norm):
        return "7_world_knowledge"
    # 3) options contain 2+ distinct proper nouns (entity-pick trivia).
    #    Each option's first capitalized word is treated as sentence-start
    #    convention, NOT a proper-noun signal.
    proper_opt_count = sum(
        1 for o in opts_norm if has_proper_noun(o, skip_first_capitalized=True)[0]
    )
    if proper_opt_count >= 2:
        return "7_world_knowledge_entities"
    return None


# ---------- Pipeline ----------
RULE_ORDER = [
    "rule1", "rule2", "rule3", "rule4", "rule5", "rule6", "rule7",
]


def evaluate(row: dict) -> str | None:
    q = row["q"]
    opts = list(row["o"])
    ci = int(row["c"])
    level = int(row["l"])
    r = rule1_well_formed(q, opts, ci)
    if r:
        return r
    correct = opts[ci]
    r = rule2_no_meta(q)
    if r:
        return r
    r = rule3_real_distractors(opts)
    if r:
        return r
    r = rule4_one_best(opts)
    if r:
        return r
    r = rule5_fits_level(correct, level)
    if r:
        return r
    r = rule6_no_specialty(correct, q)
    if r:
        return r
    r = rule7_no_world_knowledge(q, opts)
    if r:
        return r
    return None


def shuffle_options(row: dict, rng: random.Random) -> dict:
    opts = list(row["o"])
    ci = int(row["c"])
    correct = opts[ci]
    rng.shuffle(opts)
    new_ci = opts.index(correct)
    return {**row, "o": opts, "c": new_ci}


def load_raw(level: int) -> list[dict]:
    path = RAW_DIR / f"level_{level}.json"
    with path.open() as f:
        return json.load(f)


def write_canonical(rows: list[dict], path: Path) -> None:
    canonical = [
        {
            "id": str(r["i"]),
            "question": r["q"],
            "options_json": json.dumps(r["o"], ensure_ascii=False),
            "english_level": str(r["l"]),
            "correct_index": str(r["c"]),
        }
        for r in rows
    ]
    with path.open("w") as f:
        json.dump(canonical, f, ensure_ascii=False, indent=2)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SHUFFLE_SEED)

    per_level_kept: dict[int, list[dict]] = {}
    per_level_drops: dict[int, Counter] = defaultdict(Counter)
    per_level_input: dict[int, int] = {}

    sample_rng = random.Random(SHUFFLE_SEED + 1)
    for level in (1, 2, 3, 4, 5, 6):
        rows = load_raw(level)
        per_level_input[level] = len(rows)
        kept: list[dict] = []
        for row in rows:
            drop = evaluate(row)
            if drop:
                per_level_drops[level][drop] += 1
                continue
            kept.append(shuffle_options(row, rng))
        # deterministic per-level sample if over cap
        if len(kept) > PER_LEVEL_CAP:
            kept = sample_rng.sample(kept, PER_LEVEL_CAP)
            # restore by original id so output order is stable
            kept.sort(key=lambda r: r["i"])
        per_level_kept[level] = kept
        write_canonical(kept, OUT_DIR / f"level_{level}.json")

    # consolidated canonical
    all_rows: list[dict] = []
    for lvl in (1, 2, 3, 4, 5, 6):
        all_rows.extend(per_level_kept[lvl])
    write_canonical(all_rows, OUT_DIR / "all_levels.json")

    # compact runtime pool (used by index.html)
    compact_pool = [
        {"i": r["i"], "q": r["q"], "o": r["o"], "l": r["l"], "c": r["c"]}
        for r in all_rows
    ]
    with (OUT_DIR / "questions.compact.json").open("w") as f:
        json.dump(compact_pool, f, ensure_ascii=False, separators=(",", ":"))

    # report
    lines = []
    lines.append("v9 English-Only Selector — Report")
    lines.append("=" * 50)
    lines.append("")
    total_in = sum(per_level_input.values())
    total_kept = sum(len(v) for v in per_level_kept.values())
    lines.append(f"Total input:  {total_in:,}")
    lines.append(f"Total kept:   {total_kept:,}  ({total_kept / total_in:.2%})")
    lines.append("")
    lines.append(f"{'Level':<8}{'Input':>10}{'Kept':>10}{'Yield':>10}")
    for lvl in (1, 2, 3, 4, 5, 6):
        inp = per_level_input[lvl]
        kept = len(per_level_kept[lvl])
        lines.append(f"L{lvl:<7}{inp:>10,}{kept:>10,}{kept / inp:>9.2%}")
    lines.append("")
    lines.append("Drop counts per rule, per level")
    lines.append("-" * 50)
    rule_keys: list[str] = []
    seen = set()
    for lvl in (1, 2, 3, 4, 5, 6):
        for k in per_level_drops[lvl]:
            if k not in seen:
                rule_keys.append(k)
                seen.add(k)
    rule_keys.sort()
    header = f"{'Rule':<32}" + "".join(f"{f'L{l}':>9}" for l in range(1, 7)) + f"{'Total':>10}"
    lines.append(header)
    for rk in rule_keys:
        cells = []
        total = 0
        for lvl in (1, 2, 3, 4, 5, 6):
            c = per_level_drops[lvl].get(rk, 0)
            cells.append(c)
            total += c
        lines.append(f"{rk:<32}" + "".join(f"{c:>9,}" for c in cells) + f"{total:>10,}")
    lines.append("")
    (OUT_DIR / "report.txt").write_text("\n".join(lines) + "\n")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
