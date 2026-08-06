"""
check_fallback_matches.py

Usage:
    python3 check_fallback_matches.py --input rt_results.csv --output flagged_for_review.csv
"""

import re
import csv
import argparse


def normalize(title: str) -> str:
    """Loose normalization so cosmetic differences don't get flagged."""
    t = title.lower().strip()
    t = t.replace("&", "and")
    t = re.sub(r"\s*\(\d{4}\)\s*$", "", t)  # trailing "(2022)" etc.
    t = re.sub(r"[:\-–—,.!?'\"]", "", t)     # punctuation
    t = re.sub(r"\s+", " ", t)               # collapse whitespace
    return t


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to rt_results.csv")
    parser.add_argument("--output", default="flagged_for_review.csv", help="Path to write flagged rows")
    args = parser.parse_args()

    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total_ok = 0
    flagged = []

    for row in rows:
        if row.get("status") != "ok":
            continue
        total_ok += 1

        title = row.get("title", "")
        rt_title = row.get("rt_title", "")

        if normalize(title) != normalize(rt_title):
            flagged.append(row)

    if flagged:
        fieldnames = list(flagged[0].keys())
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flagged)

    print(f"Total 'ok' rows: {total_ok}")
    print(f"Flagged for review: {len(flagged)} ({len(flagged)/total_ok*100:.1f}%)")
    print(f"Written to: {args.output}")

    # Also flag not_found and error rows separately, since those are worth
    # a look too — just for a different reason (RT genuinely has no match,
    # or the request failed)
    not_found = [r for r in rows if r.get("status") == "not_found"]
    errors = [r for r in rows if r.get("status", "").startswith("error")]
    print(f"\nAlso: {len(not_found)} not_found, {len(errors)} error rows (not included in flagged file above).")


if __name__ == "__main__":
    main()