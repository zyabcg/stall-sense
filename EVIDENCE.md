# Evidence log (raw material for the DEV post)

Append as we build. Dates in IST.

## Timings
<!-- Gemma seconds per photo, TabPFN fit/predict time, on the M4 / 16 GB laptop -->
* Oct 16: gemma4:e4b with straightening + think=False: 15.3s to 23.2s per photo, avg 18.8s (12 photos).
* Oct 15: gemma4:e4b (9.5 GB download) via Ollama 0.40.4: 37.0s (tidy sheet), 42.1s (messy sheet) per photo on M4 / 16 GB.
* Oct 16: TabPFN v2 walk-forward backtest on M4 (MPS): avg 1.4s per market day (fit + predict, ~5 items), 47 market days.

## Backtest results (SIMULATED data)
* Oct 16, TabPFN v2, quick run (every 4th market day after 24-day warmup; 47 days, 246 item forecasts). Replayed against simulated true demand:

| Strategy | Waste $ | Lost profit $ | Sellouts | Profit $ | MAE vs demand |
|---|---|---|---|---|---|
| Stall Sense (TabPFN v2) | 1,636 | 2,438 | 103 | 21,062 | 4.83 |
| Bring what you sold last time | 1,428 | 4,916 | 133 | 18,792 | 6.60 |
| Bring what you brought last time | 4,003 | 1,455 | 63 | 19,678 | 8.00 |
| Vendor's own pen-and-paper loads | 3,980 | 1,512 | 54 | 19,644 | 8.20 |

  Stall Sense: +$1,418 profit (+7.2%) vs vendor, waste -59%, but MORE sellouts (103 vs 54). It trades some sellouts for much less waste. Full run + v3.5 pending.

## Failures and fixes
<!-- e.g. "Gemma misread 7 as 1 on crossed out entries, fixed with X" -->
* Oct 15 (synthetic data): first version of the simulated vendor sold out 70% of the time. Cause: basing next week's load on last week's *sales* hides true demand on sellout days, so loads ratchet down (and an item at 1 unit could never grow: 1 x 1.2 rounds to 1). Fixed by scaling from what was *brought* after a sellout and cutting back slowly. Result: 30% sellouts, $14.2k simulated waste and $9.3k simulated lost sales over 2 years. This censoring problem is also exactly why naive "bring what you sold last week" fails real vendors.

* Oct 15 (Gemma extraction, first run): 23/48 fields correct (48%) on 2 simulated tally photos. Gemma read the digits correctly but paired them with the wrong row: on a tilted photo the right-hand columns sit lower than their item name, so it read straight across and shifted every value down one row. Fix attempt 1: prompt tells it to follow the sloped ruled line.
* Oct 15 (sample photos): no freely licensed photos of a vendor tally exist online, and scoring needs known answers, so tally photos are rendered from the simulated sales in OFL handwriting fonts with tilt, perspective, shadow, blur, crossed-out numbers and "all!" for sellouts. Labeled SIMULATED. Real handwriting will be harder.

* Oct 16 (TabPFN license): a valid API key is not enough. The TabPFN-3.5 license (tabpfn-3-5-license-v1.0) must be accepted separately on ux.priorlabs.ai, and in a non-interactive terminal TabPFN can't open the browser flow, so it errors. TabPFN v2 (Apache weights) needs no gate, so we ran v2 first.
* Oct 16 (fix attempt 1 result): the "follow the sloped line" prompt helped the tidy sheet (16 -> 19/20) but Gemma got stuck printing blank lines on the messy one (64,000 lines, JSON never closed). Fixed with an output length cap (num_predict) + one retry, and think=False (also cut time from ~40s to ~21s per photo). Row shifting still happened.
* Oct 16 (fix attempt 2, the real fix): straighten the photo before Gemma sees it (extract/straighten.py: find the rotation where ink and ruled lines form the sharpest horizontal stripes; plain numpy). Result on all 12 simulated sheets: **240/256 fields correct (94%)**, avg 18.8s per photo. Tidy sheets 72/72 (100%), messy 168/184 (91%). Remaining errors: picking the crossed-out number (tally_11), one shifted row (tally_05), one misread digit.
* Oct 16: Gemma never set unsure=true, even on rows it got wrong. Self-reported confidence is unreliable, so the app flags rows with rule checks instead (sold > brought, missing price, unknown item, value far from history).

## Screenshots
<!-- docs/<file>.png: one line note -->
* docs/screen_loadlist.png: load list for a dry Saturday (TabPFN v2), ledger design with slow/busy range bars.
* docs/screen_track_record.png: backtest verdict + ledger table, full 185-day v2 run.
* docs/screen_read_tally.png: tally upload screen.
* docs/screen_mobile.png: phone width (390px).

## Cost comparison
<!-- Our cost per run ($0 local) vs closed vision API pricing for the same volume. Cite sources. -->

## Vendor feedback
<!-- Verbatim quotes, with permission -->
