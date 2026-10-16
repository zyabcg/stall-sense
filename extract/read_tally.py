"""
Read a photo of a handwritten tally sheet into table rows, using Gemma
running locally through Ollama. Nothing leaves the laptop.

Use from Python:
    from extract.read_tally import read_tally
    result = read_tally("data/samples/tally_01.jpg")

Or from the terminal:
    uv run python -m extract.read_tally data/samples/tally_01.jpg
"""

import json
import sys
import time
from typing import Optional

import ollama
from pydantic import BaseModel, Field

from extract.straighten import straighten

MODEL = "gemma4:e4b"     # change here to try a bigger/smaller Gemma

# The vendor's known items. In the app this comes from their sales history,
# so Gemma can map scribbles like "toms" or "sourdo" to a real item name.
KNOWN_ITEMS = ["kale", "tomatoes", "strawberries", "zucchini", "apples",
               "eggs", "sourdough", "honey"]


# The exact shape we want back. Ollama forces Gemma's answer to match it.
class Row(BaseModel):
    written_as: str = Field(description="item name exactly as written on the sheet")
    item: str = Field(description="matching name from the known item list, or 'unknown'")
    brought: Optional[int] = Field(description="quantity taken to market")
    sold: Optional[int] = Field(description="quantity sold")
    price: Optional[float] = Field(description="price per unit")
    unsure: bool = Field(description="true if any value in this row was hard to read")


class Tally(BaseModel):
    date_as_written: str
    market_as_written: str
    rows: list[Row]


PROMPT = f"""This is a photo of a market vendor's handwritten sales tally.
Read every item row into the schema.

Rules:
- The photo is usually tilted. Each row's values sit on the SAME ruled line
  as the item name, so follow that line across the page even if it slopes.
  Do not read straight across horizontally. The first row under the
  headers belongs to the first item.
- Columns are: item, quantity brought (may be headed "took", "in" or "brought"),
  quantity sold, and price per unit (may be headed "$", "@" or "price").
- If a number is crossed out, ignore it and use the number written next to it.
- If "sold" says "all", "SOLD OUT" or similar, sold equals brought.
- Map each item to one of these known items: {", ".join(KNOWN_ITEMS)}.
  Abbreviations are common (e.g. "toms" = tomatoes). Use "unknown" if none fit.
- Set unsure=true for any row you could not read confidently. Never guess silently.
"""


def read_tally(image_path: str, model: str = MODEL) -> dict:
    """Send one photo to local Gemma and return its reading plus timing."""
    start = time.perf_counter()
    level_image, tilt = straighten(image_path)   # rotate the page level first
    tally = None
    for attempt in range(2):
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": PROMPT, "images": [level_image]}],
            format=Tally.model_json_schema(),
            think=False,           # answer directly; thinking was slow and looped
            # num_predict caps the answer length: once Gemma got stuck
            # printing blank lines forever. A short retry nudge fixes it.
            options={"temperature": 0 if attempt == 0 else 0.3, "num_predict": 1500},
        )
        try:
            tally = Tally.model_validate_json(response.message.content)
            break
        except ValueError:
            continue
    seconds = time.perf_counter() - start
    if tally is None:
        raise RuntimeError(f"Gemma returned unreadable output for {image_path}")

    # "all" / "SOLD OUT" safety net, in case the model left sold empty.
    for row in tally.rows:
        if row.sold is None and row.brought is not None and not row.unsure:
            row.unsure = True
    return {"tally": tally.model_dump(), "seconds": round(seconds, 1),
            "model": model, "tilt_corrected_deg": tilt}


if __name__ == "__main__":
    print(json.dumps(read_tally(sys.argv[1]), indent=2))
