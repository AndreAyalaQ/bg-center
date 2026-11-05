"""Generate fact and aggregate eval questions from member frontmatter.

Expected answers are computed from the data, so they stay correct when a
member file changes. Re-run after editing any member doc.

    python evals/generate_fact_questions.py                      # sample data
    python evals/generate_fact_questions.py --data ../bg-center-data/members \
        --out ../bg-center-data/golden.generated.yaml               # real data
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "sample" / "members"
DEFAULT_OUT = ROOT / "evals" / "sample_golden.generated.yaml"
HAND_WRITTEN = ROOT / "evals" / "sample_golden.yaml"

# Accepted spellings when the model answers in the other language.
CITY_ALIASES = {
    "Lisboa": ["Lisboa", "Lisbon"],
    "Porto": ["Porto", "Oporto"],
    "Braga": ["Braga"],
    "Coimbra": ["Coimbra"],
    "Amesterdão": ["Amesterdão", "Amsterdam"],
}


def load_members(data_dir: Path) -> list[dict[str, Any]]:
    members = []
    for path in sorted(data_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"{path.name}: missing frontmatter")
        _, front, _ = text.split("---", 2)
        meta = yaml.safe_load(front)
        meta["_file"] = path.name
        members.append(meta)
    if not members:
        raise SystemExit(f"No member files found in {data_dir}")
    return members


def first(m: dict[str, Any]) -> str:
    name: str = m["name"].split()[0]
    return name


def names(ms: list[dict[str, Any]]) -> list[str]:
    return [first(m) for m in ms]


def per_member(m: dict[str, Any]) -> list[dict[str, Any]]:
    mid, fn, nick = m["id"], first(m), m["nickname"]
    city = m["city"]
    out: list[dict[str, Any]] = [
        {
            "id": f"fact-city-{mid}",
            "category": "single_fact",
            "language": "en",
            "question": f"Where does {nick} live?",
            "expected_members": [mid],
            "must_contain_any": CITY_ALIASES.get(city, [city]),
        },
        {
            "id": f"fact-city-pt-{mid}",
            "category": "single_fact",
            "language": "pt",
            "question": f"Em que cidade vive {fn}?",
            "expected_members": [mid],
            "must_contain_any": CITY_ALIASES.get(city, [city]),
        },
        {
            "id": f"fact-job-{mid}",
            "category": "single_fact",
            "language": "en",
            "question": f"What does {fn} do for work?",
            "expected_members": [mid],
            "judge_rubric": f"States that {fn} works as a {m['job']} (any language).",
        },
        {
            "id": f"fact-nickname-{mid}",
            "category": "single_fact",
            "language": "en",
            "question": f"Who is {nick}?",
            "expected_members": [mid],
            "must_contain": [fn],
        },
    ]

    if "pets" not in m:
        out.append({
            "id": f"unans-pets-{mid}",
            "category": "unanswerable",
            "language": "en",
            "question": f"Does {fn} have any pets?",
            "expected_members": [mid],
            "expect_decline": True,
        })
    elif not m["pets"]:
        out.append({
            "id": f"fact-pets-{mid}",
            "category": "single_fact",
            "language": "en",
            "question": f"Does {fn} have any pets?",
            "expected_members": [mid],
            "judge_rubric": f"Says {fn} has no pets.",
        })
    else:
        pet_names = [p.split(":", 1)[1].strip() for p in m["pets"]]
        out.append({
            "id": f"fact-pets-{mid}",
            "category": "single_fact",
            "language": "en",
            "question": f"Does {fn} have any pets?",
            "expected_members": [mid],
            "must_contain": pet_names,
        })
    return out


def aggregates(ms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_ids = [m["id"] for m in ms]
    by_bday = sorted(ms, key=lambda m: m["birthday"])
    by_height = sorted(ms, key=lambda m: m["height_cm"])

    lisboa = [m for m in ms if m["city"] == "Lisboa"]
    veg = [m for m in ms if m.get("diet") == "vegetarian"]
    cats = [m for m in ms if any(p.startswith("cat") for p in m.get("pets") or [])]

    return [
        {
            "id": "agg-oldest",
            "category": "cross_member",
            "language": "en",
            "question": "Who is the oldest in the group?",
            "expected_members": all_ids,
            "must_contain": [first(by_bday[0])],
        },
        {
            "id": "agg-youngest-pt",
            "category": "cross_member",
            "language": "pt",
            "question": "Quem é o mais novo do grupo?",
            "expected_members": all_ids,
            "must_contain": [first(by_bday[-1])],
        },
        {
            "id": "agg-tallest",
            "category": "cross_member",
            "language": "en",
            "question": "Who is the tallest?",
            "expected_members": all_ids,
            "must_contain": [first(by_height[-1])],
        },
        {
            "id": "agg-shortest",
            "category": "cross_member",
            "language": "en",
            "question": "Who is the shortest?",
            "expected_members": all_ids,
            "must_contain": [first(by_height[0])],
        },
        {
            "id": "agg-lisboa",
            "category": "cross_member",
            "language": "en",
            "question": "Who lives in Lisbon?",
            "expected_members": [m["id"] for m in lisboa],
            "must_contain": names(lisboa),
        },
        {
            "id": "agg-vegetarians-pt",
            "category": "cross_member",
            "language": "pt",
            "question": "Quem é vegetariano no grupo?",
            "expected_members": [m["id"] for m in veg],
            "must_contain": names(veg),
        },
        {
            "id": "agg-cats",
            "category": "cross_member",
            "language": "en",
            "question": "Who has cats?",
            "expected_members": [m["id"] for m in cats],
            "must_contain": names(cats),
        },
    ]


def check(cases: list[dict[str, Any]], member_ids: set[str]) -> None:
    ids = Counter(c["id"] for c in cases)
    dupes = [i for i, n in ids.items() if n > 1]
    if dupes:
        raise SystemExit(f"Duplicate case ids: {dupes}")
    for c in cases:
        unknown = set(c.get("expected_members", [])) - member_ids
        if unknown:
            raise SystemExit(f"{c['id']}: unknown members {unknown}")
        gradable_keys = ("must_contain", "must_contain_any", "expect_decline", "judge_rubric")
        if not any(k in c for k in gradable_keys):
            raise SystemExit(f"{c['id']}: no way to grade it")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--hand-written", type=Path, default=HAND_WRITTEN)
    args = ap.parse_args()

    members = load_members(args.data)
    generated = [q for m in members for q in per_member(m)] + aggregates(members)

    header = "# GENERATED by evals/generate_fact_questions.py. Do not edit by hand.\n"
    args.out.write_text(
        header + yaml.safe_dump(generated, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    hand: list[dict[str, Any]] = []
    if args.hand_written.exists():
        hand = yaml.safe_load(args.hand_written.read_text(encoding="utf-8"))
    all_cases = hand + generated
    check(all_cases, {m["id"] for m in members})

    summary = (
        f"{len(members)} members · {len(generated)} generated · "
        f"{len(hand)} hand-written · {len(all_cases)} total"
    )
    print(summary)
    for cat, n in sorted(Counter(c["category"] for c in all_cases).items()):
        print(f"  {cat:<14} {n}")
    print(f"wrote {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")


if __name__ == "__main__":
    main()
