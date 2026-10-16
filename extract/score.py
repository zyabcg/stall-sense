"""
Score Gemma's readings against the known answers in data/samples/labels.json.
Produces the extraction accuracy numbers for EVIDENCE.md and the post.

Run:  uv run python -m extract.score            (all sample photos)
      uv run python -m extract.score tally_01.jpg tally_05.jpg
"""

import json
import sys
from pathlib import Path

from extract.read_tally import MODEL, read_tally

SAMPLES = Path(__file__).parent.parent / "data" / "samples"
FIELDS = ["item", "brought", "sold", "price"]


def score_sheet(truth_rows: list[dict], read_rows: list[dict]) -> dict:
    """Field-level accuracy: for each true row, did Gemma get each field right?"""
    by_item = {r["item"]: r for r in read_rows}
    correct, total, unsure_flags, missed = 0, 0, 0, []
    for truth in truth_rows:
        got = by_item.get(truth["item"])
        for field in FIELDS:
            total += 1
            if got is None:
                continue
            if field == "price":
                ok = got["price"] is not None and abs(got["price"] - truth["price"]) < 0.01
            else:
                ok = got[field] == truth[field]
            correct += ok
            if not ok:
                missed.append(f"{truth['item']}.{field}: want {truth[field]}, got {got[field]}")
        if got is None:
            missed.append(f"{truth['item']}: row missing")
        elif got["unsure"]:
            unsure_flags += 1
    extra = len([r for r in read_rows if r["item"] not in {t["item"] for t in truth_rows}])
    return {"correct": correct, "total": total, "unsure_rows": unsure_flags,
            "extra_rows": extra, "errors": missed}


if __name__ == "__main__":
    labels = json.loads((SAMPLES / "labels.json").read_text())
    names = sys.argv[1:] or sorted(labels)
    all_correct = all_total = 0
    times = []
    for name in names:
        result = read_tally(str(SAMPLES / name))
        s = score_sheet(labels[name]["rows"], result["tally"]["rows"])
        all_correct += s["correct"]
        all_total += s["total"]
        times.append(result["seconds"])
        print(f"{name} [{labels[name]['difficulty']}]: {s['correct']}/{s['total']} fields, "
              f"{result['seconds']}s, unsure rows {s['unsure_rows']}, extra rows {s['extra_rows']}")
        for e in s["errors"]:
            print("   x", e)
    print(f"\nModel {MODEL}: {all_correct}/{all_total} fields correct "
          f"({all_correct / all_total:.0%}), avg {sum(times) / len(times):.1f}s per photo")
