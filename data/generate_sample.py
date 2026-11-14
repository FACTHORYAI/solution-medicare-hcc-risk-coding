"""Generate the synthetic sample: invented clinical notes and the tables derived from them.

Everything here is invented. No real patient, note or record is used. The notes are put
together from sentence templates and a small vocabulary of problems; the answers a text model
would give for each note are written from the same templates, so they are exact. Run it from
the repository root:

    uv run python data/generate_sample.py

It writes data/sample/*.parquet (notes_raw, notes, patient_status, hcc_weights, icd10_codes,
demographics, patient_profiles, patient_risk, raf_bands, hcc_distribution, graph_nodes,
graph_edges) and tests/recorded_answers.json. The same seed always gives the same files.

How the tables are made:

- The generator writes the notes and, per note and per task, the JSON answer a text model would
  return. The two model jobs then read those answers through the recorded text model, so the
  extracted tables have the rows and the row order the jobs produce, and nothing is rejected.
- Every other table is made by the repository's own jobs, in their order: prepare_notes,
  build_patient_profiles, calculate_raf, raf_summary, hcc_distribution and
  build_knowledge_graph.
- Every chunk an answer names stands in its note exactly as written, and the first place it
  stands is the sentence that mentions it, so the graph's evidence spans can be found by text
  search. The generator stops when that does not hold.
- A few rows of notes_raw have no note id, no patient id or no text, so prepare_notes has
  something to drop.

What is real and what is not:

- The ICD-10-CM codes are real, public codes with descriptions written from the author's
  memory; they are not checked against the current release of the code set.
- The HCC numbers follow the CMS-HCC version 24 numbering as the author knows it. Four of them
  (18, 19, 35 and 40) have a weight in the simplified risk model; the others (85, 96 and 111)
  have none, so they count as 0 in it. No CMS mapping table is copied or included.
- The age and sex weights are illustrative, apart from the one published cell (female, 70 to
  74: 0.346); see raf.py.
- The patients, their ages, their problems and their notes are invented.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from medicare_hcc_risk_coding import raf
from medicare_hcc_risk_coding.jobs import REGISTRY, call_run
from medicare_hcc_risk_coding.schemas import (
    HCC_WEIGHTS,
    NOTES_RAW,
    PATIENT_STATUS,
)
from medicare_hcc_risk_coding.text.recorded import RecordedTextModel

SEED = 20251201
N_PATIENTS = 150
REPO = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO / "data" / "sample"
ANSWERS_PATH = REPO / "tests" / "recorded_answers.json"


# The twelve notes the repository started with, kept word for word. Their answers are the
# recorded ones, with the two family-history chunks changed to the words the note uses.
# fmt: off
HAND_NOTES: list[dict] = [
    {
        "patient_id": "p001",
        "text": "Chief Complaint: follow-up of diabetes. The patient is a 72-year-old female with type 2 diabetes mellitus with diabetic mononeuropathy and Crohn's disease of the small intestine without complications. Both conditions remain active and are managed with current therapy. Plan: continue medications and review in three months.",
        "problems": [
            ("type 2 diabetes mellitus with diabetic mononeuropathy", 'E11.41', 18, 'Present', 0.95),
            ("Crohn's disease of the small intestine without complications", 'K50.00', 35, 'Present', 0.92),
        ],
        "demographics": ('female', 72, 0.95),
        "status": ('CFA', '0', True),
    },
    {
        "patient_id": "p002",
        "text": "Chief Complaint: routine diabetes review. The patient is a 68-year-old male with type 2 diabetes mellitus without complications, well controlled on metformin. Plan: continue current therapy and repeat labs in six months.",
        "problems": [
            ("type 2 diabetes mellitus without complications", 'E11.9', 19, 'Present', 0.94),
        ],
        "demographics": ('male', 68, 0.94),
        "status": ('CND', '1', False),
    },
    {
        "patient_id": "p003",
        "text": "Chief Complaint: joint pain. The patient is a 79-year-old female with rheumatoid arthritis of unspecified site with involvement of other organs and systems, and type 2 diabetes mellitus without complications. Both are active problems. Plan: adjust disease-modifying therapy and follow up.",
        "problems": [
            ("rheumatoid arthritis of unspecified site with involvement of other organs and systems", 'M05.60', 40, 'Present', 0.93),
            ("type 2 diabetes mellitus without complications", 'E11.9', 19, 'Present', 0.9),
        ],
        "demographics": ('female', 79, 0.93),
        "status": ('CPA', '2', True),
    },
    {
        "patient_id": "p004",
        "text": "Chief Complaint: blood pressure check. The patient is a 65-year-old male with essential hypertension and hyperlipidaemia, both controlled. No other chronic conditions are reported. Plan: continue current therapy.",
        "problems": [
            ("essential hypertension", 'I10', None, 'Present', 0.96),
            ("hyperlipidaemia", 'E78.5', None, 'Present', 0.9),
        ],
        "demographics": ('male', 65, 0.96),
        "status": ('CFA', '3', False),
    },
    {
        "patient_id": "p005",
        "text": "Chief Complaint: diabetes follow-up. The patient is an 81-year-old female with type 2 diabetes mellitus with chronic complications, including retinopathy. Her mother had diabetes. Plan: continue insulin and ophthalmology review.",
        "problems": [
            ("type 2 diabetes mellitus with chronic complications", 'E11.41', 18, 'Present', 0.92),
            ("mother had diabetes", 'Z83.3', None, 'Family', 0.9),
        ],
        "demographics": ('female', 81, 0.92),
        "status": ('CND', '0', True),
    },
    {
        "patient_id": "p006",
        "text": "Chief Complaint: bowel symptoms review. The patient is a 74-year-old male with a history of Crohn's disease of the small intestine, in remission for several years, and essential hypertension. Plan: continue blood pressure therapy, no bowel therapy needed.",
        "problems": [
            ("Crohn's disease of the small intestine", 'K50.00', 35, 'Past', 0.9),
            ("essential hypertension", 'I10', None, 'Present', 0.95),
        ],
        "demographics": ('male', 74, 0.95),
        "status": ('CPA', '1', False),
    },
    {
        "patient_id": "p007",
        "text": "Chief Complaint: arthritis follow-up. The patient is an 88-year-old female with rheumatoid arthritis of unspecified site with involvement of other organs and systems, currently on biologic therapy. Plan: continue treatment and monitor.",
        "problems": [
            ("rheumatoid arthritis of unspecified site with involvement of other organs and systems", 'M05.60', 40, 'Present', 0.91),
        ],
        "demographics": ('female', 88, 0.91),
        "status": ('CFA', '2', True),
    },
    {
        "patient_id": "p008",
        "text": "Chief Complaint: diabetes and kidney review. The patient is a 70-year-old male with type 2 diabetes mellitus with diabetic chronic kidney disease, stage three. Plan: continue nephroprotective therapy.",
        "problems": [
            ("type 2 diabetes mellitus with diabetic chronic kidney disease", 'E11.22', 18, 'Present', 0.93),
        ],
        "demographics": ('male', 70, 0.93),
        "status": ('CND', '3', False),
    },
    {
        "patient_id": "p009",
        "text": "Chief Complaint: colitis follow-up. The patient is a 76-year-old female with ulcerative colitis, unspecified, currently active. Plan: continue mesalazine and review in three months.",
        "problems": [
            ("ulcerative colitis, unspecified", 'K51.90', 35, 'Present', 0.9),
        ],
        "demographics": ('female', 76, 0.9),
        "status": ('CPA', '0', True),
    },
    {
        "patient_id": "p010",
        "text": "Chief Complaint: annual review. The patient is a 63-year-old male with type 2 diabetes mellitus without complications. His father had colorectal cancer. Plan: continue metformin and routine screening.",
        "problems": [
            ("type 2 diabetes mellitus without complications", 'E11.9', 19, 'Present', 0.94),
            ("father had colorectal cancer", 'Z80.0', None, 'Family', 0.9),
        ],
        "demographics": ('male', 63, 0.94),
        "status": ('CFA', '1', False),
    },
    {
        "patient_id": "p011",
        "text": "Chief Complaint: multiple chronic conditions review. The patient is an 84-year-old female with type 2 diabetes mellitus with chronic complications and rheumatoid arthritis of unspecified site with involvement of other organs and systems. Both conditions are active. Plan: continue current therapy.",
        "problems": [
            ("type 2 diabetes mellitus with chronic complications", 'E11.41', 18, 'Present', 0.92),
            ("rheumatoid arthritis of unspecified site with involvement of other organs and systems", 'M05.60', 40, 'Present', 0.9),
        ],
        "demographics": ('female', 84, 0.92),
        "status": ('CND', '2', True),
    },
    {
        "patient_id": "p012",
        "text": "Chief Complaint: diabetes review. The patient is a 67-year-old male with type 2 diabetes mellitus without complications. Plan: continue current therapy.",
        "problems": [
            ("type 2 diabetes mellitus without complications", 'E11.9', 19, 'Present', 0.95),
        ],
        "demographics": ('male', 67, 0.95),
        "status": ('CPA', '3', False),
    },
]
# fmt: on


@dataclass(frozen=True)
class Problem:
    """One problem the notes can name: its code, HCC number and the words a note uses for it."""

    code: str
    hcc: int | None
    full: str  # as a note names it when it is present
    short: str  # as a note names it when it is past, absent, possible and so on
    family: str  # a note names at most one problem of a family
    extras: tuple[str, ...] = ()  # the assertions besides Present that the problem may take
    share: int = 1  # how often it is picked within its family


# fmt: off
PROBLEMS: list[Problem] = [
    # HCC 19: diabetes without complication.
    Problem("E11.9", 19, "type 2 diabetes mellitus without complications", "type 2 diabetes mellitus", "diabetes", ("Absent", "Hypothetical", "Possible"), 8),
    Problem("E10.9", 19, "type 1 diabetes mellitus without complications", "type 1 diabetes mellitus", "diabetes", ("Absent",), 1),
    # HCC 18: diabetes with chronic complications.
    Problem("E11.22", 18, "type 2 diabetes mellitus with diabetic chronic kidney disease", "type 2 diabetes mellitus", "diabetes", (), 2),
    Problem("E11.41", 18, "type 2 diabetes mellitus with diabetic mononeuropathy", "type 2 diabetes mellitus", "diabetes", (), 2),
    Problem("E11.42", 18, "type 2 diabetes mellitus with diabetic polyneuropathy", "type 2 diabetes mellitus", "diabetes", (), 2),
    Problem("E11.51", 18, "type 2 diabetes mellitus with diabetic peripheral angiopathy without gangrene", "type 2 diabetes mellitus", "diabetes", (), 1),
    # HCC 35: inflammatory bowel disease.
    Problem("K50.00", 35, "Crohn's disease of the small intestine without complications", "Crohn's disease of the small intestine", "ibd", ("Past", "Absent"), 3),
    Problem("K50.90", 35, "Crohn's disease without complications", "Crohn's disease", "ibd", ("Possible", "Absent", "Conditional"), 2),
    Problem("K51.90", 35, "ulcerative colitis without complications", "ulcerative colitis", "ibd", ("Past", "Possible", "Absent"), 3),
    Problem("K51.00", 35, "ulcerative pancolitis without complications", "ulcerative pancolitis", "ibd", (), 1),
    # HCC 40: rheumatoid arthritis.
    Problem("M05.60", 40, "rheumatoid arthritis of unspecified site with involvement of other organs and systems", "rheumatoid arthritis", "ra", ("Absent", "Conditional"), 2),
    Problem("M06.9", 40, "unspecified rheumatoid arthritis", "rheumatoid arthritis", "ra", ("Possible", "Absent", "Hypothetical", "Past"), 3),
    Problem("M05.79", 40, "rheumatoid arthritis with rheumatoid factor of multiple sites without organ or systems involvement", "rheumatoid arthritis", "ra", (), 1),
    # No HCC in the simplified model, and none in the CMS-HCC model either.
    Problem("I10", None, "essential hypertension", "hypertension", "hypertension", ("Absent", "Hypothetical", "Possible", "Conditional"), 1),
    Problem("E78.5", None, "hyperlipidaemia", "hyperlipidaemia", "lipids", ("Absent", "Hypothetical", "Possible"), 1),
    Problem("M19.90", None, "osteoarthritis", "osteoarthritis", "osteoarthritis", ("Absent", "Possible", "Conditional"), 1),
    Problem("E03.9", None, "hypothyroidism", "hypothyroidism", "thyroid", ("Absent", "Possible"), 1),
    Problem("K21.9", None, "gastro-oesophageal reflux disease", "gastro-oesophageal reflux disease", "reflux", ("Past", "Absent", "Conditional"), 1),
    # HCC numbers that exist in CMS-HCC V24 but have no weight in the simplified model.
    Problem("I50.9", 85, "unspecified heart failure", "heart failure", "heart_failure", ("Absent", "Possible", "Hypothetical", "Conditional"), 3),
    Problem("I50.22", 85, "chronic systolic heart failure", "chronic systolic heart failure", "heart_failure", (), 1),
    Problem("J44.9", 111, "chronic obstructive pulmonary disease", "COPD", "copd", ("Absent", "Possible", "Hypothetical", "Conditional"), 1),
    Problem("I48.91", 96, "unspecified atrial fibrillation", "atrial fibrillation", "afib", ("Past", "Absent", "Possible", "Conditional"), 1),
]

# How many patients, in a hundred, have a problem of the family.
PREVALENCE: dict[str, int] = {
    "diabetes": 38, "ibd": 10, "ra": 12, "hypertension": 42, "lipids": 30, "osteoarthritis": 20,
    "thyroid": 12, "reflux": 12, "heart_failure": 10, "copd": 10, "afib": 7,
}

# (code, as a note writes it); a family history never has an HCC.
FAMILY_HISTORY: list[tuple[str, str]] = [
    ("Z83.3", "family history of diabetes"),
    ("Z80.0", "family history of colorectal cancer"),
    ("Z82.61", "family history of arthritis"),
    ("Z83.79", "family history of inflammatory bowel disease"),
    ("Z82.49", "family history of heart disease"),
]
RELATIVES = ["mother", "father", "sister", "brother"]

COMPLAINTS: dict[str, list[str]] = {
    "diabetes": ["diabetes review", "follow-up of diabetes", "blood sugar check"],
    "ibd": ["bowel symptoms review", "colitis follow-up", "abdominal pain review"],
    "ra": ["joint pain", "arthritis follow-up", "stiff hands"],
    "hypertension": ["blood pressure check"],
    "lipids": ["cholesterol review"],
    "osteoarthritis": ["knee pain", "joint pain"],
    "thyroid": ["tiredness review"],
    "reflux": ["heartburn review"],
    "heart_failure": ["shortness of breath", "swelling of the legs"],
    "copd": ["breathing review", "cough follow-up"],
    "afib": ["palpitations review"],
}
GENERAL_COMPLAINTS = ["annual review", "routine check", "general check-up"]
MANY_COMPLAINTS = ["multiple chronic conditions review", "chronic conditions follow-up"]

PLANS = [
    "continue current therapy.",
    "continue current therapy and repeat labs in six months.",
    "continue medications and review in three months.",
    "adjust therapy and follow up.",
    "continue treatment and monitor.",
    "no change to therapy; review in six months.",
    "refer for a specialist opinion and review in two months.",
]
FILLERS_ONE = ["The problem is stable on current therapy.", "The problem is being managed in clinic.", "", ""]
FILLERS_MANY = ["The problems are stable on current therapy.", "All are being managed in clinic.", "", ""]
HEALTHY = ["No chronic conditions are reported.", "There are no chronic conditions on record."]

# {c} is the problem as the note writes it, {Pro} the pronoun and {pos} the possessive.
EXTRA_SENTENCES: dict[str, list[str]] = {
    "Past": ["{Pro} had {c} several years ago, and it has resolved.", "History of {c}, which resolved after treatment.", "Previous {c}, now resolved."],
    "Absent": ["{Pro} has no history of {c}.", "No history of {c} is reported.", "There is no history of {c}."],
    "Possible": ["Possible {c}; tests are planned to confirm.", "Findings may suggest {c}, to be confirmed with tests."],
    "Hypothetical": ["Should {c} develop, a specialist referral will be arranged.", "{Pro} was advised to call if {c} is suspected."],
    "Conditional": ["Symptoms of {c} appear only during flares.", "{Pro} notes {c} symptoms only when under stress."],
}
FAMILY_SENTENCES = ["There is a {c}, in {pos} {relative}.", "{Pro} reports a {c} in {pos} {relative}."]
EXTRA_WEIGHTS = [("Past", 18), ("Family", 22), ("Absent", 20), ("Possible", 14), ("Hypothetical", 13), ("Conditional", 13)]
# fmt: on

BY_FAMILY: dict[str, list[Problem]] = {}
for _problem in PROBLEMS:
    BY_FAMILY.setdefault(_problem.family, []).append(_problem)
NAMES: dict[int, str] = dict(raf.HCC_NAMES)


@dataclass
class Mention:
    """One problem a note names, as the text model would return it."""

    chunk: str
    code: str
    hcc: int | None
    assertion: str
    confidence: float


def _list_text(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _weighted(rng: random.Random, options: list[tuple[str, int]]) -> str:
    return rng.choices([name for name, _ in options], [weight for _, weight in options])[0]


def _confidence(rng: random.Random, assertion: str) -> float:
    if assertion in ("Possible", "Hypothetical", "Conditional"):
        return round(rng.uniform(0.72, 0.88), 2)
    return round(rng.uniform(0.86, 0.97), 2)


def _pick_present(rng: random.Random) -> list[Problem]:
    """Choose the problems a patient has, at most one per family and at most four."""
    if rng.random() < 0.04:
        return []
    while True:
        chosen = []
        for family, percent in PREVALENCE.items():
            if rng.random() * 100 < percent:
                options = BY_FAMILY[family]
                chosen.append(rng.choices(options, [p.share for p in options])[0])
        if chosen:
            break
    while len(chosen) > 4:
        chosen.pop(rng.randrange(len(chosen)))
    return chosen


def _next_present(rng: random.Random, present: list[Problem]) -> list[Problem]:
    """The problems of a patient's second note: the same, one fewer or one more."""
    draw = rng.random()
    if draw < 0.5 or not present:
        return list(present)
    if draw < 0.7 and len(present) > 1:
        kept = list(present)
        kept.pop(rng.randrange(len(kept)))
        return kept
    families = {p.family for p in present}
    options = [f for f in PREVALENCE if f not in families]
    if not options or len(present) >= 4:
        return list(present)
    family = rng.choice(options)
    pool = BY_FAMILY[family]
    return [*present, rng.choices(pool, [p.share for p in pool])[0]]


def _complaint(rng: random.Random, present: list[Problem]) -> str:
    if len(present) >= 3:
        return rng.choice(MANY_COMPLAINTS)
    if not present:
        return rng.choice(GENERAL_COMPLAINTS)
    return rng.choice(COMPLAINTS[present[0].family])


def make_note(
    rng: random.Random, person: dict, present: list[Problem]
) -> tuple[str, list[Mention]]:
    """Write one note and the problems a text model would return for it.

    Every chunk is the exact words of the note, and the first place it stands is the sentence
    that mentions it.
    """
    pronoun, possessive = ("She", "her") if person["gender"] == "female" else ("He", "his")
    article = "an" if str(person["age"]).startswith("8") else "a"
    sentences: list[tuple[str, list[str]]] = []  # (sentence, the chunks it holds)
    mentions: list[Mention] = []

    def mention(chunk: str, code: str, hcc: int | None, assertion: str) -> None:
        mentions.append(Mention(chunk, code, hcc, assertion, _confidence(rng, assertion)))

    sentences.append((f"Chief Complaint: {_complaint(rng, present)}.", []))
    who = f"The patient is {article} {person['age']}-year-old {person['gender']}"
    if present:
        head, tail = present[:3], present[3:]
        sentences.append(
            (f"{who} with {_list_text([p.full for p in head])}.", [p.full for p in head])
        )
        if tail:
            sentences.append(
                (
                    f"Active problems also include {_list_text([p.full for p in tail])}.",
                    [p.full for p in tail],
                )
            )
        fillers = FILLERS_MANY if len(present) > 1 else FILLERS_ONE
        filler = rng.choice(fillers)
        if filler:
            sentences.append((filler, []))
        for p in present:
            mention(p.full, p.code, p.hcc, "Present")
    else:
        sentences.append((f"{who} seen for a routine check. {rng.choice(HEALTHY)}", []))

    used = {p.family for p in present}
    used_history: set[str] = set()
    for _ in range(rng.choice([0, 0, 1, 1, 1, 2])):
        assertion = _weighted(rng, EXTRA_WEIGHTS)
        candidates = [p for p in PROBLEMS if assertion in p.extras and p.family not in used]
        if assertion != "Family" and not candidates:
            assertion = "Family"
        if assertion == "Family":
            options = [h for h in FAMILY_HISTORY if h[0] not in used_history]
            if not options:
                continue
            code, phrase = rng.choice(options)
            used_history.add(code)
            text = rng.choice(FAMILY_SENTENCES).format(
                c=phrase, Pro=pronoun, pos=possessive, relative=rng.choice(RELATIVES)
            )
            mention(phrase, code, None, "Family")
            sentences.append((text, [phrase]))
            continue
        problem = rng.choice(candidates)
        used.add(problem.family)
        text = rng.choice(EXTRA_SENTENCES[assertion]).format(c=problem.short, Pro=pronoun)
        mention(problem.short, problem.code, problem.hcc, assertion)
        sentences.append((text, [problem.short]))

    sentences.append((f"Plan: {rng.choice(PLANS)}", []))

    text = " ".join(sentence for sentence, _ in sentences)
    offset = 0
    for sentence, chunks in sentences:
        for chunk in chunks:
            found = text.find(chunk)
            if not offset <= found < offset + len(sentence):
                message = f"chunk {chunk!r} first stands outside its sentence in {text!r}"
                raise SystemExit(message)
        offset += len(sentence) + 1
    return text, mentions


def make_person(rng: random.Random, patient_id: str) -> dict:
    gender = rng.choice(["female", "male"])
    age = rng.randint(60, 64) if rng.random() < 0.06 else rng.randint(65, 95)
    if age < 65:
        eligibility, orec = "CND", "1"
    else:
        eligibility = rng.choices(["CNA", "CND", "CFA", "CPA"], [60, 10, 18, 12])[0]
        orec = rng.choices(["0", "1", "2", "3"], [80, 15, 3, 2])[0]
    return {
        "patient_id": patient_id,
        "gender": gender,
        "age": age,
        "status": (eligibility, orec, eligibility in ("CFA", "CPA")),
    }


def _demographics_answer(rng: random.Random, person: dict) -> dict:
    return {
        "gender": person["gender"],
        "age": person["age"],
        "confidence": round(rng.uniform(0.9, 0.97), 2),
    }


def _answers(mentions: list[Mention]) -> str:
    return json.dumps(
        [
            {
                "chunk": m.chunk,
                "icd10_code": m.code,
                "hcc": m.hcc,
                "assertion": m.assertion,
                "confidence": m.confidence,
            }
            for m in mentions
        ]
    )


def generate() -> dict:
    """Invent the patients and their notes; return the raw rows, the statuses and the answers."""
    rng = random.Random(SEED)
    raw: list[dict] = []
    statuses: list[dict] = []
    answers: dict[str, dict[str, str]] = {"extract_icd10": {}, "infer_demographics": {}}
    seen_texts: set[str] = set()

    def add(note_id: str, patient_id: str, text: str, mentions: list[Mention], demo: dict) -> None:
        raw.append({"note_id": note_id, "patient_id": patient_id, "text": text})
        answers["extract_icd10"][text] = _answers(mentions)
        answers["infer_demographics"][text] = json.dumps(demo)
        seen_texts.add(text)

    for hand in HAND_NOTES:
        mentions = [Mention(c, code, hcc, a, conf) for c, code, hcc, a, conf in hand["problems"]]
        for m in mentions:
            if hand["text"].find(m.chunk) < 0:
                message = f"chunk {m.chunk!r} is not in the note of {hand['patient_id']}"
                raise SystemExit(message)
        gender, age, confidence = hand["demographics"]
        demo = {"gender": gender, "age": age, "confidence": confidence}
        add(f"note_{hand['patient_id']}", hand["patient_id"], hand["text"], mentions, demo)
        eligibility, orec, medicaid = hand["status"]
        statuses.append(
            {
                "patient_id": hand["patient_id"],
                "eligibility": eligibility,
                "orec": orec,
                "medicaid": medicaid,
            }
        )

    def fresh_note(person: dict, present: list[Problem]) -> tuple[str, list[Mention]]:
        for _ in range(50):
            text, mentions = make_note(rng, person, present)
            if text not in seen_texts:
                return text, mentions
        raise SystemExit("could not write a note that differs from the earlier ones")

    for index in range(len(HAND_NOTES) + 1, N_PATIENTS + 1):
        patient_id = f"p{index:03d}"
        person = make_person(rng, patient_id)
        present = _pick_present(rng)
        text, mentions = fresh_note(person, present)
        add(f"note_{patient_id}", patient_id, text, mentions, _demographics_answer(rng, person))
        if rng.random() < 0.47:
            text, mentions = fresh_note(person, _next_present(rng, present))
            add(
                f"note_{patient_id}_2",
                patient_id,
                text,
                mentions,
                _demographics_answer(rng, person),
            )
        eligibility, orec, medicaid = person["status"]
        statuses.append(
            {
                "patient_id": patient_id,
                "eligibility": eligibility,
                "orec": orec,
                "medicaid": medicaid,
            }
        )

    # Rows prepare_notes drops: a missing or empty note id, patient id or text.
    ghost = make_person(rng, "p151")
    for note_id, patient_id, blank in (
        (None, "p151", "text"),
        ("", "p152", "text"),
        ("note_p153", None, "text"),
        ("note_p154", "p154", ""),
        ("note_p155", "p155", None),
    ):
        text, _ = make_note(rng, ghost, _pick_present(rng))
        raw.append(
            {
                "note_id": note_id,
                "patient_id": patient_id,
                "text": text if blank == "text" else blank,
            }
        )
    return {"raw": raw, "statuses": statuses, "answers": answers}


def _run(name: str, inputs: dict[str, pa.Table], model: RecordedTextModel | None = None) -> dict:
    spec = REGISTRY[name]
    return call_run(spec, inputs, spec.params_cls(), model)


def build_tables(data: dict) -> dict[str, pa.Table]:
    """Run the repository's own jobs over the generated notes and return every sample table."""
    model = RecordedTextModel(data["answers"])
    tables: dict[str, pa.Table] = {
        "notes_raw": pa.Table.from_pylist(data["raw"], schema=NOTES_RAW),
        "patient_status": pa.Table.from_pylist(data["statuses"], schema=PATIENT_STATUS),
        "hcc_weights": pa.Table.from_pylist(
            [
                {"hcc": hcc, "hcc_name": NAMES[hcc], "weight": weight}
                for hcc, weight in sorted(raf.HCC_WEIGHTS.items())
            ],
            schema=HCC_WEIGHTS,
        ),
    }
    tables.update(_run("prepare_notes", {"notes_raw": tables["notes_raw"]}))
    notes = {"notes": tables["notes"]}
    coded = _run("extract_icd10", notes, model)
    demographics = _run("infer_demographics", notes, model)
    for name in ("rejected_icd10", "rejected_demographics"):
        rejected = (coded | demographics)[name]
        if rejected.num_rows:
            raise SystemExit(
                f"{name} has {rejected.num_rows} rejected rows: {rejected.to_pylist()[:3]}"
            )
    tables["icd10_codes"] = coded["icd10_codes"]
    tables["demographics"] = demographics["demographics"]
    for name, inputs in (
        ("build_patient_profiles", ("icd10_codes", "demographics", "patient_status")),
        ("calculate_raf", ("patient_profiles",)),
        ("raf_summary", ("patient_risk",)),
        ("hcc_distribution", ("patient_profiles", "hcc_weights")),
        ("build_knowledge_graph", ("notes", "icd10_codes", "demographics", "hcc_weights")),
    ):
        tables.update(_run(name, {key: tables[key] for key in inputs}))
    return tables


def main() -> None:
    data = generate()
    tables = build_tables(data)
    answers = json.dumps(data["answers"], indent=2, ensure_ascii=False) + "\n"
    ANSWERS_PATH.write_text(answers, encoding="utf-8")
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        pq.write_table(table, SAMPLE_DIR / f"{name}.parquet")
        print(f"{name}: {table.num_rows} rows")
    digest = hashlib.sha256()
    for path in sorted(SAMPLE_DIR.glob("*.parquet")):
        digest.update(path.read_bytes())
    print(f"sha256 of the sample: {digest.hexdigest()[:16]}", file=sys.stderr)


if __name__ == "__main__":
    main()
