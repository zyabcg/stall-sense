# Evidence log (raw material for the DEV post)

Append as we build. Dates in IST.

## Timings
<!-- Gemma seconds per photo, TabPFN fit/predict time, on the M4 / 16 GB laptop -->

## Failures and fixes
<!-- e.g. "Gemma misread 7 as 1 on crossed out entries, fixed with X" -->
* Oct 15 (synthetic data): first version of the simulated vendor sold out 70% of the time. Cause: basing next week's load on last week's *sales* hides true demand on sellout days, so loads ratchet down (and an item at 1 unit could never grow: 1 x 1.2 rounds to 1). Fixed by scaling from what was *brought* after a sellout and cutting back slowly. Result: 30% sellouts, $14.2k simulated waste and $9.3k simulated lost sales over 2 years. This censoring problem is also exactly why naive "bring what you sold last week" fails real vendors.

## Screenshots
<!-- docs/<file>.png: one line note -->

## Cost comparison
<!-- Our cost per run ($0 local) vs closed vision API pricing for the same volume. Cite sources. -->

## Vendor feedback
<!-- Verbatim quotes, with permission -->
