# CLAUDE.md: Market Day Planner (Hacktoberfest 2026, Week 2: Side Hustle)

You are my build partner for a contest entry. Read this whole file before doing anything. It holds every decision already made, the contest rules, and the submission template. Keep it updated as decisions change (log changes in the "Decision Log" at the bottom).

My name is Parth. I am a finance student, comfortable with tech but not a full time developer. Explain what you're doing in plain language, keep me in the loop on decisions, and never silently cut scope.

---

## 1. The contest

**Challenge:** Hacktoberfest Open-Source AI Challenge, Week 2 (DEV.to)
**Link:** https://dev.to/challenges/hacktoberfest-week2-2026-10-12
**Theme:** Side Hustle. Build something with open-weight models or open-source AI that someone would actually pay for.
**Start:** Oct 12, 2026
**Submissions due:** Oct 18, 2026 (I'm in IST, UTC+5:30. Verify the exact deadline timezone on the challenge page. Plan to submit by Oct 18 afternoon IST.)
**Winners:** week of Oct 19

### Core rule
Open-source AI must be at the core of the product: an open-weight model, an open-source agent framework, local inference, or a combo. "The open pieces should be what makes your project work."

Using Claude Code as the dev tool is fine. The *product* must run on open models. Never add a closed model API (OpenAI, Anthropic, Gemini API, etc.) into the product runtime.

### What judges want
1. Small, specific, useful. A real problem for a real person (freelancer, small business owner, niche community).
2. A post explaining **why open innovation matters** for this build: cost low enough for the business to work, data privacy, fine-tuning for a niche, no lock-in, runs offline. Show where open beat closed.
3. **Bonus:** land a first user. Did they use it, would they pay, what did they ask for next.

### Judging criteria
1. **Writing Quality (weighted most heavily)**
2. Relevance to the Prompt and Theme
3. Creativity
4. Technical Execution
5. Use of Partner Technology (optional)

Implication: a working, focused build plus an excellent post beats a flashy build with a lazy post. Budget real time for writing. Capture evidence while building (see section 7).

### Prizes
Overall winner: $250 + DEV++ + badge. Partner category winners: $200 (featured) or $100.

### Categories we are entering
**Locked:**
1. **Best Use of Gemma ($200):** Gemma runs locally and reads the handwritten tally photos. Core of the product.
2. **Best Use of TabPFN ($200):** TabPFN forecasts quantities. Prior Labs strongly recommends TabPFN-3.5 (sign up at platform.priorlabs.ai, accept the free non-commercial license for the key). They favor TabPFN used inside a wider prediction agent.
3. **Best Use of a .tech Domain ($100):** put the demo live on a free .tech domain from hacktoberfest.com/my/promos and link it in the post. (Renews at $29.99/yr. Remind me to turn off auto renew after the contest.)
4. **Best Use of Entire ($100):** share the agent sessions behind the project in the write-up.

**Stretch (only if ahead of schedule by Thursday Oct 15):**
5. **Tinker ($200):** fine-tune Gemma on messy handwritten tallies and show a clear before/after improvement over baseline. Needs labeled handwriting samples.
6. **Render ($200):** host the public demo front end. Be clear in the post that the real product runs locally.
7. **Sentry Agent Tracing ($100):** show latency, tokens, cost per run with traces/screenshots. Could double as proof for the "$0 to run" argument.

**Skipping:** DigitalOcean, MongoDB, Tiger Data, Mastra, Temporal, ElevenLabs, SerpApi, Backboard, Arduino, GitHub Copilot. They are forced fits or contradict the "data stays on your laptop" story. Do not add them.

---

## 2. The product

**Working name:** Market Day Planner (final name TBD. Candidates: Stall Sense, Haul, Load Out. Help me pick one early since it drives the domain, repo, and post title.)

**User:** farmers market vendors (small growers, bakers, makers who sell at weekly markets). Global audience. A weekly sabzi or organic market vendor in Noida has the identical problem and can be our local first user.

**Problem:** every week a vendor guesses how much of each item to load. Overload means unsold produce that spoils. Underload means selling out by 10am and losing sales. Vendor guides tell them to compare last week's sales and rainy markets to rainy markets, but they do it on pen and paper. No product we found does per item "what to bring" forecasting for a single vendor.

**What it does:**
1. Vendor snaps a photo of their handwritten sales tally after a market.
2. **Gemma (local, vision)** reads it into structured rows: date, market, item, quantity brought, quantity sold, price.
3. Vendor reviews and corrects the extracted rows (low confidence fields flagged).
4. **TabPFN (local)** predicts how much of each item to bring next market, using past sales, day, season, weather, and which market.
5. Output: a clear load list. Example: "Kale: bring 35 bunches (last 3 rainy Saturdays you sold 28 to 33)."

**Who pays and why it works as a business:** a $5 to $10/month tool only works if inference costs nothing. Open models running locally make the unit economics possible.

### MVP scope (must ship)
1. Photo upload → Gemma extraction → editable table
2. CSV history store (local file)
3. TabPFN forecast per item for the next market, with a simple confidence range
4. Load list output (screen + downloadable)
5. Backtest view: our forecast vs naive baseline ("bring what you sold last week") on historical data, showing leftover units, sellouts, and money wasted
6. Runs fully offline after first setup

### Not in MVP
Accounts, multi user, cloud sync, mobile app, payments. Do not build these.

---

## 3. Tech stack and decisions

1. **Language:** Python.
2. **UI:** Streamlit (fastest path). Switch only if there is a real reason, and tell me first.
3. **Gemma:** run locally via Ollama. Pick a **vision capable** Gemma variant sized to my hardware. Check what's currently available on Ollama rather than assuming a version. Start with the smallest vision model that reads handwriting acceptably; measure before upgrading.
4. **TabPFN:** `pip install tabpfn`, run locally.
   * Use **TabPFN-3.5** for the demo (Prior Labs' recommendation for their prize). Requires accepting the license at platform.priorlabs.ai on first run.
   * **Licensing angle for the post:** TabPFN-2.5, 2.6, 3 weights are non-commercial. TabPFN-2 weights are Apache 2.0 with an attribution requirement, so a paid version of this tool could legally ship on v2. Build so the model version is a single config switch, and if time allows, show v2 vs 3.5 accuracy.
   * **Offline:** run each model once with internet so weights cache, then confirm it works with network off. Cache location can be set with `TABPFN_MODEL_CACHE_DIR`.
   * CPU is fine for our data size (small datasets, a few hundred rows). GPU optional. If CPU is too slow, tell me.
   * Verify current TabPFN API and docs before coding against it; do not rely on memory.
5. **Weather feature:** for historical data generation, use a free historical weather source (check availability, e.g. Open-Meteo). In the app, the vendor can type the expected weather for next market so the app still works offline.
6. **Repo:** public GitHub repo. Never commit model weights, API keys, or tokens. Use `.env` and `.gitignore`.
7. **Cost rule:** total spend must be ₹0. No paid APIs. If anything would cost money or needs a card, stop and ask me first.

### Suggested repo structure
```
/app            Streamlit app
/extract        Gemma tally reading (prompt, parsing, validation)
/forecast       TabPFN features, training, prediction, backtest
/data
  /synthetic    generator + generated CSVs
  /real         real vendor data (gitignored if private)
  /samples      sample tally photos for the demo
/docs           screenshots, diagrams for the post
EVIDENCE.md     running log for the write-up (see section 7)
POST_DRAFT.md   the DEV post, filled in as we go
README.md
CLAUDE.md       this file
```

---

## 4. Data plan

No public dataset exists at per vendor, per item level (only market wide aggregates). So:

1. **Synthetic base (build first):** a generator that produces a realistic season or two of weekly sales for one vendor across a few items. Ground it in reality: real historical weather for a real market city, real crop seasonality (items in and out of season), market attendance effects (rain, holidays, heat), and realistic noise and sellouts (sold quantity is capped by quantity brought, which matters for forecasting). Label it clearly as simulated everywhere it appears.
2. **Sample tally photos:** I will handwrite realistic tally sheets (messy, abbreviations, crossings out) and photograph them. These test Gemma extraction and feed the demo. If we attempt Tinker, these plus labels become the fine-tuning set.
3. **Real vendor data (parallel):** I'll try to get photos of a real vendor's notebook (local market vendor and/or online vendor communities). Build so real data drops in through the same pipeline.

Never present synthetic data or results as real. Honesty reads well in the post.

---

## 5. Evaluation (this produces the post's headline number)

1. Backtest walk forward: for each past market, train on prior weeks only, predict, compare to actual.
2. Baseline: "bring what you sold last week" and "bring what you brought last week."
3. Metrics: MAE per item, total leftover units, number of sellouts, estimated money wasted (unsold × cost) and money lost (sellout lost sales).
4. Gemma extraction accuracy on the sample tally photos: field level accuracy, time per photo on my laptop.
5. If Tinker happens: same extraction metrics, before vs after fine-tuning.

Report numbers honestly, including where the model does worse than baseline.

---

## 6. Schedule (today is Tue Oct 13)

| Day | Goal |
|---|---|
| Tue 13 | Hardware check, setup Ollama + Gemma + TabPFN, claim .tech domain + credits, pick name, repo, synthetic data generator |
| Wed 14 | Gemma extraction pipeline on sample photos, TabPFN forecast + backtest working |
| Thu 15 | Streamlit UI end to end, offline test. Decide on Tinker / Render stretch |
| Fri 16 | Show it to a real vendor if possible, capture feedback and a quote. Deploy demo to .tech domain |
| Sat 17 | Write the post, record 60 to 90 second demo video, finalize agent session |
| Sun 18 | Polish, final checks, submit early (IST afternoon) |

If we slip, cut stretch goals first, never the post quality or the backtest.

---

## 7. Evidence capture (do this continuously)

Maintain `EVIDENCE.md`. Append as we go:
1. Timings (Gemma seconds per photo, TabPFN fit/predict time, on my hardware)
2. Failures and fixes (e.g. "Gemma misread 7 as 1 on crossed out entries, fixed with X")
3. Screenshots saved to /docs with a one line note each
4. Cost comparison: our cost per run ($0 local) vs what a closed vision API would charge for the same volume (look up current pricing, cite the source)
5. Any vendor quotes or feedback, verbatim with permission

### Agent sessions
The post template asks for an agent session saved with DevRelay, and the Entire category rewards sharing agent sessions. Before heavy building starts, check DevRelay's and Entire's docs for how to capture **Claude Code** sessions, tell me the steps, and set it up so early sessions aren't lost.

---

## 8. Writing rules for the post (and README)

1. No em dashes. Avoid unnecessary dashes in general.
2. Plain, human, specific. No hype words ("revolutionary", "game changer", "delve", "leverage").
3. Global audience: explain the vendor's problem in a line or two so anyone gets it.
4. Lead with the real problem and a concrete number, not the tech.
5. Honest about limits: synthetic data is labeled, failures are mentioned, Claude Code is credited as the dev tool while the product runs on open models.
6. Required tags: #devchallenge and #hf26challenge (the template adds them).

---

## 9. Submission template (fill in POST_DRAFT.md as we build)

```
*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I Built
<!-- What does it do, and who would pay for it?  What problem does it solve for them? -->

## Demo
<!-- Share a deployed link or a video demo. -->

## Code
<!-- Show us the code!  You can embed a GitHub repo directly into your post. -->

## How I Built It
<!-- Which open-source AI did you use (open-weight models, agent harnesses, frameworks, local inference), and how is your project built around it? -->

## Why Does Open Innovation Matter?
<!-- Why does open innovation matter for what you built?  What did it make possible that a closed API wouldn't? -->

## My Agent Session
<!-- Optional, but judges love it.  Save your session with DevRelay and embed it with the agent_session tag (see the challenge page), or link to it. -->

## My First User
<!-- Optional, but this is where bonus points live.  Did someone use it?  Who were they, what did they say, and did they pay?  If not, remove this section. -->

## Prize Categories
<!-- Which partner categories are you entering?  List every one that applies, or remove this section. -->

<!-- Team Submissions: Please pick one member to publish the submission and credit teammates by listing their DEV usernames directly in the body of the post. -->
```

### What each section should contain for us
* **What I Built:** the vendor's weekly guessing problem, what the tool does, who pays and how much.
* **Demo:** .tech domain link + short video.
* **Code:** GitHub repo embed.
* **How I Built It:** Gemma (local vision) → editable table → TabPFN (local) forecast → load list. Real timings, a failure story, the backtest.
* **Why Open Innovation Matters:** cost (unit economics of a cheap tool), privacy (sales data stays on the laptop), offline capable, TabPFN v2 Apache weights make a paid version legal, swap or fine-tune models freely. Include the closed API cost comparison.
* **My Agent Session:** DevRelay embed / Entire link.
* **My First User:** only if real. Otherwise delete the section.
* **Prize Categories:** Gemma, TabPFN, .tech Domain, Entire (+ Tinker / Render / Sentry only if actually done).

---

## 10. Your first actions in this session

1. Check my hardware yourself (OS, RAM, CPU, GPU/VRAM, free disk) and recommend the Gemma size accordingly.
2. Ask me: how comfortable I am with Python, how many hours a day I have till Sunday, whether I have a real vendor lined up.
3. Help me pick the final name.
4. Set up the repo structure, `.gitignore`, `EVIDENCE.md`, `POST_DRAFT.md`.
5. Set up agent session capture (section 7).
6. Install and smoke test Ollama + Gemma vision and TabPFN.
7. Start the synthetic data generator.

Work in small, testable steps. After each milestone, update the schedule status below and tell me what's next.

---

## Status
* [ ] Hardware checked, model sizes chosen
* [ ] Name picked, repo created
* [ ] .tech domain + partner credits claimed
* [ ] Agent session capture set up
* [ ] Ollama + Gemma vision working
* [ ] TabPFN working offline
* [ ] Synthetic data generator
* [ ] Sample tally photos created
* [ ] Gemma extraction pipeline + accuracy measured
* [ ] Forecast + backtest vs baseline
* [ ] Streamlit app end to end
* [ ] Offline test passed
* [ ] Demo deployed on .tech domain
* [ ] Real vendor feedback (bonus)
* [ ] Demo video
* [ ] Post written and reviewed
* [ ] Submitted

## Decision Log
* Oct 13: Idea locked: Market Day Planner for farmers market vendors (global framing).
* Oct 13: Stack: Gemma (local, Ollama) + TabPFN (local) + Streamlit. Zero cost rule.
* Oct 13: Categories: Gemma, TabPFN, .tech, Entire locked. Tinker, Render, Sentry stretch.
* Oct 13: Claude Code is the dev tool only; no closed models in the product runtime.
