"""
Make realistic photos of handwritten tally sheets. ALL IMAGES ARE SIMULATED.

Why: no freely licensed photos of a market vendor's sales notebook exist
online, and to MEASURE how well Gemma reads a sheet we need to know the
correct answer. So we render sheets from the simulated sales history in
handwriting fonts, then make them messy like a real phone photo:
abbreviations, crossed-out numbers, "SOLD OUT" notes, a tilted page,
shadows, blur and JPEG compression.

Run:  uv run python data/samples/make_tallies.py
Out:  data/samples/tally_01.jpg ... and data/samples/labels.json (the answers)
"""

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
SALES_CSV = HERE.parent / "synthetic" / "SIMULATED_sales_portland_or.csv"
FONTS = sorted((HERE / "fonts").glob("*.ttf"))
N_SHEETS = 12
SEED = 7

# How a busy vendor might scribble each item name.
ABBREVIATIONS = {
    "kale": ["kale", "Kale", "kale bunch"],
    "tomatoes": ["toms", "tomatos", "Tomatoes"],
    "strawberries": ["strawb", "strawbs", "Strwberries"],
    "zucchini": ["zukes", "zucc", "Zucchini"],
    "apples": ["apples", "Apls", "apples kg"],
    "eggs": ["eggs", "eggs (doz)", "Eggs"],
    "sourdough": ["sourdo", "loaves", "Sourdough"],
    "honey": ["honey", "hny jars", "Honey"],
}
MARKET_NAMES = {"saturday_market": ["Sat mkt", "SAT", "Saturday market"],
                "wednesday_market": ["Wed mkt", "WED", "Wednesday"]}


def handwritten(draw_on: Image.Image, xy, text, font, ink, rng):
    """Paste text with a slight random tilt and size wobble, like a pen."""
    size = int(font.size * rng.uniform(0.92, 1.08))
    f = font.font_variant(size=size)
    box = f.getbbox(text)
    w, h = box[2] + 20, box[3] + 20
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((10, 10), text, font=f, fill=ink)
    layer = layer.rotate(rng.uniform(-3, 3), expand=True, resample=Image.BICUBIC)
    x, y = xy
    draw_on.alpha_composite(layer, (int(x + rng.uniform(-4, 4)), int(y + rng.uniform(-4, 4))))
    return f.getlength(text)


def strike(draw_on: Image.Image, x, y, width, font, ink):
    """A pen line through a mistaken number."""
    d = ImageDraw.Draw(draw_on)
    mid = y + font.size * 0.75
    d.line([(x - 3, mid + 4), (x + width + 6, mid - 4)], fill=ink, width=4)


def render_sheet(day: pd.DataFrame, rng: random.Random, messy: bool):
    """Draw one market day's tally on lined paper. Returns image + answer rows."""
    W, H = 1200, 1600
    paper = Image.new("RGBA", (W, H), (248, 245, 232, 255))
    d = ImageDraw.Draw(paper)
    for y in range(180, H, 70):                       # ruled lines
        d.line([(0, y), (W, y)], fill=(170, 195, 230, 255), width=2)
    d.line([(110, 0), (110, H)], fill=(225, 140, 140, 255), width=3)   # margin

    font = ImageFont.truetype(str(rng.choice(FONTS)), 58)
    ink = rng.choice([(25, 35, 90, 255), (20, 20, 20, 255), (40, 40, 120, 255)])

    first = day.iloc[0]
    date_fmt = rng.choice(["%d/%m/%y", "%a %d %b", "%m-%d"])
    header = f"{pd.Timestamp(first['date']).strftime(date_fmt)}   {rng.choice(MARKET_NAMES[first['market']])}"
    if first["rain_mm"] > 5 and rng.random() < 0.6:
        header += "  (rain!)"
    handwritten(paper, (140, 95), header, font, ink, rng)

    cols = {"item": 140, "took": 560, "sold": 760, "price": 980}
    labels = [("item", "item"), ("took", rng.choice(["took", "brought", "in"])),
              ("sold", "sold"), ("price", rng.choice(["$", "price", "@"]))]
    for key, text in labels:
        handwritten(paper, (cols[key], 190), text, font, ink, rng)

    answers = []
    rows = day.sample(frac=1, random_state=rng.randint(0, 9999)) if messy else day
    for i, (_, r) in enumerate(rows.iterrows()):
        y = 265 + i * 70
        handwritten(paper, (cols["item"], y), rng.choice(ABBREVIATIONS[r["item"]]), font, ink, rng)

        took = str(int(r["brought"]))
        if messy and rng.random() < 0.3:              # wrong number, crossed out
            wrong = str(int(r["brought"]) + rng.choice([-3, -2, 2, 5]))
            wlen = handwritten(paper, (cols["took"], y), wrong, font, ink, rng)
            strike(paper, cols["took"], y, wlen, font, ink)
            handwritten(paper, (cols["took"] + wlen + 18, y), took, font, ink, rng)
        else:
            handwritten(paper, (cols["took"], y), took, font, ink, rng)

        if r["sold_out"] and messy and rng.random() < 0.5:
            handwritten(paper, (cols["sold"], y), rng.choice(["all", "SOLD OUT", "all!"]), font, ink, rng)
        else:
            handwritten(paper, (cols["sold"], y), str(int(r["sold"])), font, ink, rng)

        price = f"{r['price']:g}" if rng.random() < 0.5 else f"{r['price']:.2f}"
        handwritten(paper, (cols["price"], y), price, font, ink, rng)

        answers.append({"item": r["item"], "brought": int(r["brought"]),
                         "sold": int(r["sold"]), "price": float(r["price"])})
    return paper, answers


def find_coeffs(src, dst):
    """Maths for a perspective warp (page photographed at a slight angle)."""
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.array(m, dtype=float)
    B = np.array(src, dtype=float).reshape(8)
    return np.linalg.solve(A, B).tolist()


def photograph(paper: Image.Image, rng: random.Random) -> Image.Image:
    """Make the clean sheet look like a phone photo on a table."""
    W, H = paper.size
    j = lambda: rng.uniform(0, 60)
    src = [(0, 0), (W, 0), (W, H), (0, H)]
    dst = [(j(), j()), (W - j(), j()), (W - j(), H - j()), (j(), H - j())]
    warped = paper.transform((W, H), Image.PERSPECTIVE, find_coeffs(src, dst),
                             Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    warped = warped.rotate(rng.uniform(-6, 6), expand=True, resample=Image.BICUBIC)

    table = Image.new("RGBA", (warped.width + 160, warped.height + 160),
                      rng.choice([(110, 85, 60, 255), (70, 70, 75, 255), (150, 140, 120, 255)]))
    table.alpha_composite(warped, (80, 80))
    photo = table.convert("RGB")

    # Uneven light: darken one side, like a hand or phone casting a shadow.
    shade = np.linspace(rng.uniform(0.65, 0.85), 1.0, photo.width)
    if rng.random() < 0.5:
        shade = shade[::-1]
    arr = np.asarray(photo).astype(float) * shade[None, :, None]
    photo = Image.fromarray(arr.clip(0, 255).astype("uint8"))
    photo = photo.filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 1.6)))
    return photo.resize((photo.width * 3 // 4, photo.height * 3 // 4))


if __name__ == "__main__":
    rng = random.Random(SEED)
    sales = pd.read_csv(SALES_CSV)
    days = sales[["date", "market"]].drop_duplicates().sample(N_SHEETS, random_state=SEED)

    labels = {}
    for n, (_, key) in enumerate(days.iterrows(), start=1):
        day = sales[(sales.date == key.date) & (sales.market == key.market)]
        messy = n % 3 != 1                            # 1 in 3 sheets is tidy
        paper, answers = render_sheet(day, rng, messy)
        name = f"tally_{n:02d}.jpg"
        photograph(paper, rng).save(HERE / name, quality=rng.randint(60, 85))
        labels[name] = {"date": key.date, "market": key.market,
                        "difficulty": "messy" if messy else "tidy",
                        "rows": answers, "data_source": "SIMULATED"}
        print(f"{name}: {key.date} {key.market} ({len(answers)} items, {labels[name]['difficulty']})")

    (HERE / "labels.json").write_text(json.dumps(labels, indent=2))
    print("Wrote labels.json (the correct answers, for scoring Gemma)")
