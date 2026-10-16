"""
Stall Sense: the app. Everything runs on this laptop (Gemma via Ollama,
TabPFN locally). No internet needed after setup.

Run:  uv run streamlit run app/app.py
"""

import html
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from extract.read_tally import KNOWN_ITEMS, read_tally  # noqa: E402
from forecast.config import MODEL_VERSION  # noqa: E402
from forecast.model import add_features, recommend  # noqa: E402

HERE = Path(__file__).parent
HISTORY = ROOT / "data" / "history.csv"          # the vendor's own data (gitignored)
STARTER = ROOT / "data" / "synthetic" / "SIMULATED_sales_portland_or.csv"
UPLOADS = ROOT / "data" / "real" / "uploads"
DOCS = ROOT / "docs"

st.set_page_config(page_title="Stall Sense", page_icon=str(HERE / "static" / "favicon.png"), layout="wide")
st.markdown(f"<style>{(HERE / 'style.css').read_text()}</style>", unsafe_allow_html=True)


def show(markup: str):
    # Flatten the HTML: indented lines would be rendered as a Markdown code block.
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# History: a plain CSV on this laptop
# ---------------------------------------------------------------------------
@st.cache_data
def load_history() -> pd.DataFrame:
    if not HISTORY.exists():
        pd.read_csv(STARTER).to_csv(HISTORY, index=False)   # demo starts from simulated data
    return pd.read_csv(HISTORY)


def save_rows(new_rows: pd.DataFrame):
    hist = pd.read_csv(HISTORY)
    pd.concat([hist, new_rows], ignore_index=True).to_csv(HISTORY, index=False)
    load_history.clear()


history = load_history()
simulated = (history["data_source"] == "SIMULATED").any()
n_markets = history["date"].nunique()

# ---------------------------------------------------------------------------
# Masthead
# ---------------------------------------------------------------------------
show(f"""
<div class="masthead">
  <div class="dateline">
    <span>{date.today():%A %d %B %Y}</span>
    <span>Gemma reads · TabPFN {MODEL_VERSION} forecasts · nothing leaves this laptop</span>
  </div>
  <div class="wordmark">Stall <em>Sense</em></div>
  <p class="standfirst">Photograph Saturday's tally. Get Wednesday's load list.
  Stop guessing how much kale goes in the van.</p>
</div>
""")
if simulated:
    show(f'<span class="stamp">Demo data · simulated</span>'
         f'<span class="stamp-note">{n_markets} market days of a made-up vendor, with real weather. '
         f'Your own tallies replace it.</span>')

tab_plan, tab_read, tab_bt = st.tabs(["Pack for next market", "Read a tally", "Track record"])


# ---------------------------------------------------------------------------
# Pack: next market -> TabPFN -> load list
# ---------------------------------------------------------------------------
def reason(hist: pd.DataFrame, market: str, item: str, rainy: bool) -> str:
    past = hist[(hist["market"] == market) & (hist["item"] == item)]
    similar = past[(past["rain_mm"] > 5) == rainy].tail(3)
    if similar.empty:
        return "No similar markets yet."
    kind = "rainy" if rainy else "dry"
    lo, hi = int(similar["sold"].min()), int(similar["sold"].max())
    sold_out = int(similar["sold_out"].sum())
    note = f"Last {len(similar)} {kind} markets: sold {lo}–{hi}."
    if sold_out:
        note += f" <b>Sold out {sold_out}×</b>, so demand ran higher."
    return note


def range_bar(low: float, typical: float, high: float, bring: int, scale: float) -> str:
    start = low * 0.5                     # zoom in: start the scale below the slow-day figure
    pct = lambda v: f"{max(0.0, min(100.0, 100 * (v - start) / (scale - start))):.1f}%"
    return f"""
    <div class="range">
      <div class="track"></div>
      <div class="span" style="left:{pct(low)};width:calc({pct(high)} - {pct(low)})"></div>
      <div class="mid" style="left:{pct(typical)}"></div>
      <div class="pick" style="left:{pct(bring)}"></div>
      <div class="lab" style="left:{pct(low)}">{int(low)} slow</div>
      <div class="lab" style="left:{pct(high)}">{int(high)} busy</div>
    </div>"""


def market_label(m: str) -> str:
    return m.replace("_", " ").capitalize()


with tab_plan:
    show('<div class="kicker">Next market</div><div class="section-title">What goes in the van</div>')
    markets = sorted(history["market"].unique())
    c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1])
    market = c1.selectbox("Market", markets, format_func=market_label, key="plan_market")
    last_day = pd.to_datetime(history["date"]).max().date()
    day = c2.date_input("Date", value=last_day + timedelta(days=7))
    temp = c3.number_input("Forecast high °C", value=18.0, key="plan_temp")
    rain = c4.number_input("Forecast rain, mm", value=0.0, min_value=0.0, key="plan_rain")

    recent = history[(history["market"] == market) &
                     (pd.to_datetime(history["date"]) >= pd.Timestamp(last_day) - pd.Timedelta(days=35))]
    c5, c6 = st.columns([3, 1])
    items = c5.multiselect("Items this week (in season)", sorted(history["item"].unique()),
                           default=sorted(recent["item"].unique()))
    holiday = c6.checkbox("Holiday this week")

    if items and st.button("Make the load list", type="primary"):
        info = history.groupby("item")[["unit", "price", "unit_cost"]].last()
        upcoming = pd.DataFrame([{
            "date": day.isoformat(), "weekday": day.strftime("%a"), "market": market, "item": i,
            "unit": info.loc[i, "unit"], "price": info.loc[i, "price"], "unit_cost": info.loc[i, "unit_cost"],
            "temp_max_c": temp, "rain_mm": rain, "holiday_week": holiday, "data_source": "FORECAST",
        } for i in items])
        both = add_features(pd.concat([history, upcoming], ignore_index=True))
        with st.spinner("Forecasting on this laptop…"):
            rec = recommend(both[both["data_source"] != "FORECAST"], both[both["data_source"] == "FORECAST"])
        st.session_state["load"] = (market, day, rain, rec.sort_values("bring", ascending=False))

    if "load" in st.session_state:
        market_, day_, rain_, rec = st.session_state["load"]
        lines = []
        for r in rec.itertuples():
            scale = max(r.high, r.bring) * 1.12
            lines.append(f"""
            <div class="line">
              <div><div class="qty">{r.bring}</div><div class="unit">{html.escape(str(r.unit))}</div></div>
              <div><div class="name">{html.escape(r.item)}</div>
                   <div class="why">{reason(history, market_, r.item, rain_ > 5)}</div></div>
              <div class="range-cell">{range_bar(r.low, r.typical, r.high, r.bring, scale)}</div>
            </div>""")
        show(f"""
        <div class="loadlist">
          <div class="head"><span style="text-align:right">Bring</span><span>Item</span>
          <span>Likely sales, slow to busy day · green mark = load</span></div>
          {''.join(lines)}
        </div>""")
        show('<p class="footnote">The load sits above a typical day for items with a fat margin: '
             'running out of honey costs more than carrying one jar home.</p>')
        text = "\n".join(f"{r.bring:>4} {r.unit:<7} {r.item}" for r in rec.itertuples())
        st.download_button("Download list", f"{market_label(market_)} · {day_:%a %d %b}\n\n{text}\n",
                           file_name=f"load_list_{day_}.txt")


# ---------------------------------------------------------------------------
# Read: photo -> Gemma -> editable table -> history
# ---------------------------------------------------------------------------
def flag_problems(rows: pd.DataFrame, hist: pd.DataFrame) -> list[str]:
    """Simple checks, because Gemma never admits when it is unsure."""
    flags = []
    for _, r in rows.iterrows():
        issues = []
        if r["item"] not in KNOWN_ITEMS:
            issues.append("unknown item")
        if pd.isna(r["brought"]) or pd.isna(r["sold"]) or pd.isna(r["price"]):
            issues.append("missing value")
        elif r["sold"] > r["brought"]:
            issues.append("sold more than brought?")
        past = hist[hist["item"] == r["item"]]
        if len(past) and pd.notna(r["price"]):
            usual = past["price"].median()
            if abs(r["price"] - usual) > 0.3 * usual:
                issues.append(f"price unusual (usually {usual:g})")
        if len(past) and pd.notna(r["brought"]) and r["brought"] > 2 * past["brought"].max():
            issues.append("far more than ever before")
        flags.append(", ".join(issues) or "✓")
    return flags


with tab_read:
    show('<div class="kicker">After market</div><div class="section-title">Read the tally</div>'
         '<p class="hint">Photo of the page, any angle. Gemma reads it on this laptop in about '
         '20 seconds, then you fix anything it got wrong.</p>')
    left, right = st.columns([1, 1.35], gap="large")
    with left:
        photo = st.file_uploader("Tally photo", type=["jpg", "jpeg", "png"])
        sample = st.selectbox("Or try a sample tally (simulated)",
                              [""] + sorted(p.name for p in (ROOT / "data" / "samples").glob("tally_*.jpg")))
        path = None
        if photo:
            UPLOADS.mkdir(parents=True, exist_ok=True)
            path = UPLOADS / photo.name
            path.write_bytes(photo.getvalue())
        elif sample:
            path = ROOT / "data" / "samples" / sample
        if path:
            st.image(str(path), width="stretch")

    with right:
        if path and st.button("Read it", type="primary"):
            with st.spinner("Reading the handwriting…"):
                st.session_state["reading"] = read_tally(str(path))
        result = st.session_state.get("reading")
        if result:
            t = result["tally"]
            show(f'<p class="hint">Read in {result["seconds"]}s by {result["model"]}. '
                 f'Header says “{html.escape(t["date_as_written"])}”, '
                 f'“{html.escape(t["market_as_written"])}”.</p>')
            rows = pd.DataFrame(t["rows"])[["written_as", "item", "brought", "sold", "price"]]
            rows["check"] = flag_problems(rows, history)
            c1, c2 = st.columns(2)
            market_day = c1.date_input("Market date", value=date.today())
            market = c2.selectbox("Market", sorted(history["market"].unique()), format_func=market_label)
            edited = st.data_editor(
                rows, num_rows="dynamic", width="stretch", hide_index=True,
                column_config={
                    "written_as": st.column_config.TextColumn("On the page", disabled=True),
                    "item": st.column_config.SelectboxColumn("Item", options=KNOWN_ITEMS),
                    "brought": st.column_config.NumberColumn("Brought"),
                    "sold": st.column_config.NumberColumn("Sold"),
                    "price": st.column_config.NumberColumn("Price", format="%.2f"),
                    "check": st.column_config.TextColumn("Check", disabled=True)})
            c3, c4 = st.columns(2)
            temp = c3.number_input("High that day °C", value=18.0)
            rain = c4.number_input("Rain that day, mm", value=0.0, min_value=0.0)
            if st.button("Add to my history"):
                units = history.groupby("item")["unit"].first()
                costs = history.groupby("item")["unit_cost"].median()
                new = edited.drop(columns=["written_as", "check"]).dropna(subset=["brought", "sold"])
                new = new.assign(
                    date=market_day.isoformat(), weekday=market_day.strftime("%a"), market=market,
                    unit=new["item"].map(units), unit_cost=new["item"].map(costs),
                    leftover=new["brought"] - new["sold"], sold_out=new["sold"] >= new["brought"],
                    temp_max_c=temp, rain_mm=rain, holiday_week=False, data_source="REAL")
                save_rows(new)
                st.success(f"Added {len(new)} lines. The next load list uses them.")


# ---------------------------------------------------------------------------
# Track record: backtest results, told plainly
# ---------------------------------------------------------------------------
NAMES = {"stall_sense": "Stall Sense", "vendor_actual": "Vendor's own guess (pen and paper)",
         "last_sold": "Bring what sold last time", "last_brought": "Bring what you brought last time"}

with tab_bt:
    show('<div class="kicker">Backtest on simulated data</div>'
         '<div class="section-title">Would it have paid off?</div>')
    files = [f for f in sorted(DOCS.glob("backtest_v*.csv"))
             if not f.stem.endswith("_rows") and not f.stem.endswith("_quick")]
    if not files:
        st.warning("Run `uv run python -m forecast.backtest` first.")
    else:
        pick = st.columns([1, 3])[0].selectbox("Model", [f.stem for f in files], index=len(files) - 1,
                            format_func=lambda s: "TabPFN " + s.split("_")[1])
        table = pd.read_csv(DOCS / f"{pick}.csv", index_col=0)
        ours, vendor = table.loc["stall_sense"], table.loc["vendor_actual"]
        gain = ours["profit_$"] - vendor["profit_$"]
        waste_cut = 1 - ours["waste_$"] / vendor["waste_$"]
        days = pd.read_csv(DOCS / f"{pick}_rows.csv")["date"].nunique()
        show(f"""<p class="verdict">Over {days} market days, Stall Sense would have earned
        <span class="g">${gain:,.0f} more</span> than the vendor's own guesses and thrown away
        <span class="g">{waste_cut:.0%} less stock</span>. It also sold out
        <span class="t">{int(ours['sellouts'] - vendor['sellouts'])} more times</span>.</p>""")

        rows = []
        for key, r in table.iterrows():
            cls = ' class="ours"' if key == "stall_sense" else ""
            worst_waste = r["waste_$"] == table["waste_$"].max()
            rows.append(f"""<tr{cls}><td>{NAMES[key]}</td>
              <td>${r['profit_$']:,.0f}</td>
              <td class="{'bad' if worst_waste else ''}">${r['waste_$']:,.0f}</td>
              <td>${r['lost_profit_$']:,.0f}</td><td>{int(r['sellouts'])}</td></tr>""")
        show(f"""<table class="ledger"><thead><tr><th>Strategy</th><th>Profit</th><th>Stock thrown away</th>
             <th>Profit lost to sellouts</th><th>Sellouts</th></tr></thead><tbody>{''.join(rows)}</tbody></table>""")

        worst = table["waste_$"].max()
        bars = "".join(
            f"""<div class="row{' ours' if k == 'stall_sense' else ''}"><span>{NAMES[k]}</span>
            <div><div class="bar" style="width:{100 * r['waste_$'] / worst:.0f}%"></div></div>
            <span class="val">${r['waste_$']:,.0f}</span></div>"""
            for k, r in table.sort_values("waste_$").iterrows())
        show(f'<div class="kicker">Stock thrown away</div><div class="bars">{bars}</div>')
        show('<p class="footnote">Method: for every market day, train only on earlier weeks, recommend a load, '
             'then replay that day against the simulated true demand. The vendor is made up; the weather is '
             'real. Stall Sense trades a few more sellouts for far less waste, because unsold produce costs '
             'this vendor more than a missed sale.</p>')
