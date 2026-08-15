"""Generate a supervised fine-tuning dataset from the curriculum RAG data.

Parses the 229 extracted chunks (plus course_index.json) into grounded
instruction/response examples covering course queries, units, outcomes,
textbooks, references, periods and L-T-P-C structure.

Outputs (in this directory):
    train.jsonl       ~80% of examples
    validation.jsonl  ~20% (disjoint from train)

Every generated answer is derived strictly from the source text. When a
field is not present, the example teaches the model the mandated fallback:
"I could not find that information in the college knowledge base."

Usage:
    python finetuning/generate_finetune_dataset.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

FALLBACK = "I could not find that information in the college knowledge base."

_COURSE_HEADER_RE = re.compile(
    r"(?m)^\s*([A-Z]{2,4}\d{3})\s+([A-Z][A-Z0-9 &/().,'-]{4,90}?)\s*$"
)
_LTPC_RE = re.compile(r"(?m)^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$")
_UNIT_RE = re.compile(r"\bUNIT\s+([IVXLCM]+)\b\s*([^\n]*)")
_TOTAL_PERIODS_RE = re.compile(r"\bTOTAL\s*:?\s*(\d+)\s*PERIODS", re.IGNORECASE)
_SECTION_RE = re.compile(
    r"\b(COURSE OBJECTIVES|UNIT\s+[IVXLCM]+\b|TEXT BOOKS?|REFERENCES?|COURSE OUTCOMES?|EMPLOYABILITY)\b",
    re.IGNORECASE,
)

SECTION_STARTERS = (
    "COURSE OBJECTIVES",
    "UNIT ",
    "TEXT BOOK",
    "REFERENCES",
    "COURSE OUTCOME",
    "EMPLOYABILITY",
)


def clean(text: str) -> str:
    text = text.replace("\ufffd", " ")
    text = text.replace("�,", "• ")
    text = text.replace("�?", "'")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def load_corpus_text() -> str:
    chunks = []
    with open(settings.curriculum_rag_jsonl, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            content = clean(item.get("content", ""))
            content = re.sub(r"^\[Page \d+[^\]]*\]\s*", "", content)
            chunks.append(f"[PAGE {item.get('page_start')}]\n{content}")
    return "\n".join(chunks)


def load_course_index() -> list[dict]:
    data = json.loads(Path(settings.curriculum_course_index_json).read_text(encoding="utf-8"))
    return data.get("courses", [])


def split_sections(block: str) -> dict[str, str]:
    """Split a course block into {OBJECTIVES, UNITS, TEXTBOOKS, REFERENCES, OUTCOMES}."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(block))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        name = m.group(1).upper()
        if name.startswith("UNIT"):
            sections.setdefault("UNITS", "")
            sections["UNITS"] += block[start:end]
        else:
            sections[name] = block[start:end]
    return {k: clean(v) for k, v in sections.items()}


def extract_units(units_text: str) -> list[dict]:
    units: list[dict] = []
    for m in _UNIT_RE.finditer(units_text):
        heading = m.group(2).strip()
        m_periods = re.search(r"(\d+)\s*$", heading)
        periods = int(m_periods.group(1)) if m_periods else None
        title = re.sub(r"\s*\d+\s*$", "", heading).strip() or "Untitled unit"
        start = m.end()
        next_m = _UNIT_RE.search(units_text, start)
        content = units_text[start : next_m.start() if next_m else len(units_text)].strip()
        units.append({"numeral": m.group(1), "title": title, "periods": periods, "content": clean(content)})
    return units


def extract_outcomes(outcomes_text: str) -> list[str]:
    lines = [clean(l) for l in outcomes_text.splitlines() if l.strip()]
    kept = [l for l in lines if re.search(r"\bCO\d+\b", l, re.IGNORECASE) or "students will be able" in l.lower()]
    return kept[:12]


def parse_course_block(text: str, code: str, title: str) -> dict | None:
    """Find the syllabus block for (code, title) and extract its fields.

    Uses the LAST occurrence of the code+title header (the syllabus section
    always follows the semester tables) and cuts the block at the next
    course header line."""
    title_words = re.sub(r"[^A-Z0-9 ]", " ", title.upper()).split()
    if not title_words:
        return None
    # header like "MA3151 MATRICES AND CALCULUS L T P C" (words may wrap lines)
    header_pat = re.compile(
        rf"(?m)^\s*{re.escape(code)}\s+{'\\s+'.join(re.escape(w) for w in title_words)}",
        re.IGNORECASE,
    )
    matches = list(header_pat.finditer(text))
    if not matches:
        return None
    start = matches[-1].start()
    after = matches[-1].end()

    next_header = _COURSE_HEADER_RE.search(text, after)
    end = next_header.start() if next_header else len(text)
    block = text[start:end]

    ltp = _LTPC_RE.search(block, after - start if after <= len(block) else 0)
    l, t, p, c = (int(x) for x in ltp.groups()) if ltp else (None, None, None, None)
    total_match = _TOTAL_PERIODS_RE.search(block)
    total_periods = int(total_match.group(1)) if total_match else None

    sections = split_sections(block)
    units = extract_units(sections.get("UNITS", ""))
    outcomes = extract_outcomes(sections.get("COURSE OUTCOMES", ""))
    objectives = sections.get("COURSE OBJECTIVES", "")

    return {
        "code": code,
        "title": clean(title),
        "ltp": (l, t, p, c),
        "total_periods": total_periods,
        "objectives": objectives,
        "units": units,
        "textbooks": sections.get("TEXT BOOKS", ""),
        "references": sections.get("REFERENCES", ""),
        "outcomes": outcomes,
    }


def unit_list_text(course: dict) -> str:
    units = course["units"]
    if not units:
        return ""
    parts = [f"{u['numeral']}. {u['title']}" for u in units]
    return "; ".join(parts)


def clip(text: str, limit: int = 700) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def course_examples(course: dict) -> list[dict]:
    ex: list[dict] = []
    code, title = course["code"], course["title"]
    name = f"{title} ({code})"

    # 1. course lookup / overview
    if course["objectives"]:
        ex.append(
            {
                "instruction": f"What is the course {code} about?",
                "output": f"The course {title} ({code}) aims to: {clip(course['objectives'], 800)}",
            }
        )

    # 2. units
    units_text = unit_list_text(course)
    if units_text:
        ex.append(
            {
                "instruction": f"What are the units in {title}?",
                "output": f"The {title} course contains {len(course['units'])} units: {units_text}.",
            }
        )
        ex.append(
            {
                "instruction": f"What is the unit structure of {code}?",
                "output": f"The course {title} ({code}) is organised as: {units_text}.",
            }
        )

    # 3. per-unit questions
    for u in course["units"]:
        if u["content"]:
            ex.append(
                {
                    "instruction": f"Which topics are covered in Unit {u['numeral']} of {title}?",
                    "output": f"Unit {u['numeral']} ({u['title']}) of {title} covers: {clip(u['content'], 600)}",
                }
            )
            ex.append(
                {
                    "instruction": f"What is Unit {u['numeral']} of {code} about?",
                    "output": f"Unit {u['numeral']} of {title} ({code}) is titled \"{u['title']}\". It covers: {clip(u['content'], 600)}",
                }
            )

    # 4. course outcomes
    if course["outcomes"]:
        ex.append(
            {
                "instruction": f"What are the course outcomes of {title}?",
                "output": "The course outcomes are:\n" + "\n".join(f"- {o}" for o in course["outcomes"]),
            }
        )

    # 5. textbooks / references
    if course["textbooks"]:
        ex.append(
            {
                "instruction": f"What textbook is recommended for {title}?",
                "output": f"The textbook(s) recommended for {title}: {clip(course['textbooks'], 600)}",
            }
        )
    else:
        ex.append(
            {
                "instruction": f"What textbook is recommended for {title}?",
                "output": FALLBACK,
            }
        )
    if course["references"]:
        ex.append(
            {
                "instruction": f"What are the references for {code}?",
                "output": f"The reference materials for {title} ({code}): {clip(course['references'], 600)}",
            }
        )

    # 6. periods / L-T-P-C
    if course["total_periods"]:
        ex.append(
            {
                "instruction": f"How many periods does {title} have?",
                "output": f"The course {title} ({code}) has a total of {course['total_periods']} periods.",
            }
        )
    else:
        ex.append(
            {
                "instruction": f"How many periods does {title} have?",
                "output": FALLBACK,
            }
        )
    if any(v is not None for v in course["ltp"]):
        l, t, p, c = course["ltp"]
        ex.append(
            {
                "instruction": f"What is the L-T-P-C structure of {code}?",
                "output": f"The L-T-P-C structure of {title} ({code}) is L={l}, T={t}, P={p}, C={c}.",
            }
        )

    return ex


def general_examples(text: str) -> list[dict]:
    """Small set of regulation-level examples (PEOs, PSOs, programme facts)."""
    ex: list[dict] = []
    peo = _section_between(text, "PROGRAM EDUCATIONAL OBJECTIVES", "PROGRAM SPECIFIC")
    if peo:
        ex.append({"instruction": "What are the program educational objectives?", "output": clip(peo, 800)})
    pso = _section_between(text, "PROGRAM SPECIFIC OUTCOMES", "CURRICULUM")
    if pso:
        ex.append({"instruction": "What are the program specific outcomes?", "output": clip(pso, 800)})
    programme_match = re.search(
        r"B\.TECH\.\s+ARTIFICIAL INTELLIGENCE AND DATA SCIENCE[\s\S]{0,120}?SEMESTER I", text
    )
    if programme_match:
        ex.append(
            {
                "instruction": "What programme is this curriculum for?",
                "output": "B.Tech. Artificial Intelligence and Data Science, Regulations 2021, Choice Based Credit System.",
            }
        )
    return ex


def _section_between(text: str, start: str, end: str) -> str:
    si = text.upper().find(start)
    if si < 0:
        return ""
    ei = text.upper().find(end, si)
    return clean(text[si : ei if ei > si else si + 900])


def refusal_examples() -> list[dict]:
    questions = [
        "What is tomorrow's college timetable?",
        "Who teaches AL3451 this semester?",
        "When are the mid-semester examination dates?",
        "What is the hostel fee for the 2026-27 session?",
        "What is the contact number of the registrar's office?",
        "When is the college cultural fest this year?",
        "What was the cutoff for AI and Data Science last year?",
        "What is the cafeteria menu today?",
    ]
    return [{"instruction": q, "output": FALLBACK} for q in questions]


def main() -> None:
    text = load_corpus_text()
    courses = load_course_index()
    print(f"corpus text: {len(text):,} chars, {len(courses)} courses in index")

    parsed = 0
    examples: list[dict] = []
    for course in courses:
        block = parse_course_block(text, course["course_code"], course["course_title"])
        if block is None:
            continue
        parsed += 1
        examples.extend(course_examples(block))
    examples.extend(general_examples(text))
    examples.extend(refusal_examples())
    print(f"parsed {parsed}/{len(courses)} course blocks, {len(examples)} raw examples")

    # dedupe while preserving order
    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for ex in examples:
        key = (ex["instruction"], ex["output"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(ex)
    print(f"{len(unique)} unique examples after dedupe")

    # deterministic 80/20 split
    import random

    rng = random.Random(42)
    shuffled = list(unique)
    rng.shuffle(shuffled)
    split = int(len(shuffled) * 0.8)
    train, validation = shuffled[:split], shuffled[split:]

    out_dir = Path(__file__).resolve().parent
    for name, rows in (("train.jsonl", train), ("validation.jsonl", validation)):
        path = out_dir / name
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps({"instruction": row["instruction"], "input": "", "output": row["output"]}, ensure_ascii=False) + "\n")
        print(f"wrote {path} ({len(rows)} examples)")

    # quick stats
    unavail = sum(1 for r in unique if r["output"] == FALLBACK)
    print(f"examples with fallback output: {unavail} ({100 * unavail / len(unique):.1f}%)")


if __name__ == "__main__":
    main()