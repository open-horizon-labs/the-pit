"""Read-only database excerpt trial; no full entries transferred."""
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).parent / "plugin/skills/export-to-pit/scripts"))
from pit_client import Client
def main():
    queries = sys.argv[1:] or ["moment you start caring", "on conflict", "5MB"]
    if len(queries) > 5:
        raise ValueError("Provide up to five queries")
    client = Client(timeout=15)
    results = []
    downloaded = 0
    for query in queries:
        started = time.monotonic()
        rows = client.search(query, 5, 100)
        groups = {}
        for row in rows:
            excerpt = row["excerpt"]
            downloaded += len(excerpt.encode())
            key = hashlib.sha256(excerpt.encode()).hexdigest()
            group = groups.setdefault(key, {"text": excerpt, "anchors": []})
            group["anchors"].append({"id": row["id"], "start": row["start_char"],
                "end": row["end_char"], "entry_characters": row["total_characters"]})
        results.append({"query": query, "returned_entries": len(rows),
            "distinct_excerpts": list(groups.values()),
            "elapsed_ms": round((time.monotonic() - started) * 1000)})
    print(json.dumps({"offset_unit": "Unicode code points; zero-based [start, end)",
        "range_location": "database substring before transfer", "full_entries_fetched": 0,
        "excerpt_bytes_downloaded": downloaded, "results": results}, ensure_ascii=False, indent=2))
if __name__ == "__main__":
    main()
