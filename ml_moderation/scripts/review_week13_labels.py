"""Review titles blind and append human labels to a separate, resumable CSV."""
import argparse
import csv
from pathlib import Path

from ml_moderation.cli_demo_v2 import COURSES
from ml_moderation.validator_v2 import ROOT

SOURCE = ROOT / "reports/week13/phase3/human_label_review.csv"
DEFAULT = ROOT / "datasets/generated/week13-human-labels.csv"
FIELDS = ("base_id", "selected_course", "material_title", "language", "expected_label",
          "human_reviewed_label", "reviewer", "reviewer_notes")
ANSWERS = {"1": "relevant", "0": "irrelevant", "a": "ambiguous"}


def key(row):
    return row["base_id"], row["selected_course"], row["language"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", required=True, help="Reviewer name or pseudonym")
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--limit", type=int, default=0, help="New labels for this session; 0 means all")
    args = parser.parse_args()
    if not args.reviewer.strip() or args.limit < 0:
        parser.error("Provide a nonempty reviewer and a nonnegative limit")
    if args.output.resolve() == SOURCE.resolve():
        parser.error("Use a separate output file")
    done = set()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.is_file() and args.output.stat().st_size:
        with args.output.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != FIELDS:
                parser.error("Output already exists with a different schema")
            done = {(row["reviewer"], *key(row)) for row in reader}
    new_file = not args.output.exists() or not args.output.stat().st_size
    with SOURCE.open(encoding="utf-8", newline="") as source:
        with args.output.open("a", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            if new_file:
                writer.writeheader()
            saved = 0
            for row in csv.DictReader(source):
                code = row["course"]
                item = {"base_id": row["base_id"], "selected_course": f"{code} — {COURSES[code]}",
                        "material_title": row["title"], "language": row["language"]}
                if (args.reviewer, *key(item)) in done:
                    continue
                print(f"\n{item['selected_course']} [{item['language']}]\n{item['material_title']}")
                while True:
                    answer = input("1 relevant / 0 irrelevant / a ambiguous / s skip / q quit: ").strip().lower()
                    if answer in (*ANSWERS, "s", "q"):
                        break
                if answer == "q":
                    break
                if answer == "s":
                    continue
                notes = input("Notes (optional): ").strip()
                writer.writerow({**item, "expected_label": row["label"], "human_reviewed_label": ANSWERS[answer],
                                 "reviewer": args.reviewer, "reviewer_notes": notes})
                file.flush()
                saved += 1
                if args.limit and saved >= args.limit:
                    break
    print(f"Saved {saved} new human label(s) to {args.output}")


if __name__ == "__main__":
    main()
