# finding duplicates of movies who have the same RT URL
import csv
import sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "rt_results.csv"

by_url = defaultdict(list)
with open(path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row.get("status") == "ok" and row.get("rt_url"):
            by_url[row["rt_url"]].append(row)

dupes = {url: rows for url, rows in by_url.items() if len(rows) > 1}
print(f"Duplicate rt_url values: {len(dupes)}")
for url, rows in list(dupes.items())[:10]:
    print(f"\n{url}")
    for r in rows:
        print(f"  tmdb_id={r['tmdb_id']}  title={r['title']!r}  year={r.get('year')}")