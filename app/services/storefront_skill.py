STOREFRONT_SKILL ="""# How to Assess Physical Presence & Location Vitality

## 0. What this skill is for

Some businesses look fine on the numbers but have a real-world problem a $500/hr advisor
would clock on a drive-by: a faded sign nobody can read from the road, a tired interior, a
storefront buried in a half-empty strip mall, a quiet garage-lined block with no foot traffic.
None of that shows up in QuickBooks. This skill is how LightSignal "does the drive-by" — it
reads imagery and nearby-business data to surface physical and environmental factors as
**hedged, low-weight, owner-confirmable observations**, never as asserted facts.

It answers two distinct questions, kept deliberately separate because they tell different stories:

- **Module 1 — Business Presentation:** how the business *itself* presents (its own building, sign, interior).
- **Module 2 — Location Vitality:** how alive the *environment* around it is (the block, the mall, the corridor).

A beautiful business on a dead block and a tired business on a great block are different
situations the owner needs told differently. The skill scores and surfaces them separately.

---

## 0.5. Three pieces, three homes (who runs this, and where the parts live)

This is the part most likely to be misread, so it's stated plainly. There are **three distinct
things**, each with its own home. They are not the same thing.

1. **The Classifier (already exists).** Produces the business's dimensions — `urban_density`,
   `operational_model`, `geographic_context`. We do **not** rebuild any of that. A few of those
   facts are **passed as input** to the enrichment agent (below) so it can aim its lookups
   (radius by density tier; which rubric items apply by operational model). The Classifier runs
   first; it hands off; it does not do the seeing.

2. **This skill file (just created — the instruction manual).** The granular how-to: the rubric,
   radius-scaling, frontage logic, fairness contract, confidence/suppression rules, output shape.
   It lives in the `claude skills` folder alongside `how_to_compute_kpis_canonically`,
   `how_to_visualize_a_financial_insight`, etc., and is invoked at runtime (Option 1 pattern:
   inline in the executing agent's system prompt at request time, per Agent Migration Tracker
   §1G). This knowledge did **not** exist anywhere in the project before; this file is it.

3. **A new enrichment agent (to be built — the worker).** The thing that actually executes:
   takes the Classifier's facts, pulls the imagery + nearby-business data, calls **Fable 5** to
   read the images, calls **Opus** to fuse the reads into the hedged output per this skill, and
   writes the result to the Memory layer. Dual-backend, async, on-event — the **same shape as
   DIA**. Its system prompt is thin (trigger, routing, write learnings); the heavy domain
   knowledge lives in the skill (piece 2), not the prompt.

**One-line model:** the Classifier feeds it a few facts → the skill tells it how to do the work →
the enrichment agent is the worker that runs it → output flows to Memory → dreaming → living
summary → every agent. The skill never needs to know about tabs; surfacing is the consuming
agents' job (§9).

### Why the executor is a new agent, not the Classifier (the correction)
An earlier draft said "the Classifier invokes this." That was wrong: the Classifier is a
**synchronous text-reasoning agent with no vision** — it literally cannot look at a storefront
photo. The seeing must be a **Fable 5** call; the spatial counting is plain backend code; the
fusion is an **Opus** reasoning step. Bolting a vision sub-call + image-fetch onto the Classifier
muddies a clean agent and puts it on the wrong (synchronous) cycle. So the executor is its own
**dual-backend enrichment agent**, parallel to DIA, that *feeds* the Classifier's
`geographic_context` rather than *being* the Classifier.

### §0.5 OPEN DECISION (not yet ratified): formal 9th agent vs. named enrichment step
DIA earned its own roster slot for reasons that **all apply here too**: categorically different
job (enrichment, not reasoning), runs async on-event (not the refresh cycle), dual-backend, writes
to the knowledge layer. On that parallel, this is recommended as a **formal 9th agent** in
`Agent_Migration_Master_Tracker_v2.md` ("Claude-native, no migration, just a build"). The
alternative — an anonymous backend job that calls the models directly — works but breaks roster
discipline (every other Fable/Opus-invoking, learning-writing process is a named agent). **Jaret
to ratify: 9th agent (recommended) vs. named backend step.**

---

## 1. Scope, ownership, and non-goals

- **The skill is agent-agnostic knowledge; the executor is the new enrichment agent** (§0.5).
  The agent receives the Classifier's output as input and uses it to aim its lookups; it does not
  re-run classification, and the Classifier does not run the assessment.
- **This is NOT the Document Intelligence Agent's job.** DIA reads uploaded documents. This runs
  off the business's location + online presence. Do not bolt it onto DIA.
- **Output destination:** findings are written as **learnings into the customer's Memory
  namespace** (same path DIA's document learnings take). The nightly **dreaming** pass promotes
  durable ones into the **living summary**, which every agent reads on every session. So the FA
  can later say "your signage may be limiting walk-ins," the Orchestrator can fold "you're on a
  quiet block" into a Business Health watch area, Scenario Lab can factor location into a
  relocation what-if — none of them re-deriving it.

**Non-goals (explicitly out of scope):**
- Measuring the business's own foot traffic — that comes from **POS data**, not this skill.
- Naming or classifying specific competitors — we cannot match our own classifier granularity
  for a business that isn't our user (see §6). This skill produces *density*, not *competitor identity*.
- Seasonality / footfall-over-time — no clean source; the owner's own POS history is the right
  source for their seasonality. Out of scope here.
- Any judgment about the people in an area (see §5, Fairness Contract).

---

## 2. The grounding contract (inherits anti_hallucination_rules)

This skill is a strict application of `anti_hallucination_rules`, adapted for visual + spatial data.

- **Self-assessed confidence is the prime directive here.** Before any observation, the model
  must rate whether it can *clearly see the thing it is assessing*. If the image is obstructed,
  wrong-angle, low-resolution, dark, shows a different business, or is too stale to trust → it
  **suppresses the observation** rather than guessing. A suppressed observation is the correct,
  safe outcome. Honest "couldn't get a clear look" beats a confident wrong read.
- **Type mapping (per anti_hallucination_rules §4):**
  - Observed physical facts (sign present/absent, storefront visibly boarded, X permanently-closed
    businesses within radius) are **Type-1-like** — verified-in-source or null. Never invent.
  - Interpretive reads ("interior appears dated," "block reads as quiet") are **Type-2-like** —
    permitted *only* with grounding, and every one must carry a `basis` field naming the specific
    observable(s) it rests on (e.g., "two neighboring units show CLOSED_PERMANENTLY; exterior
    image shows empty lot"). No basis → no observation.
- **Convergent signals.** Environmental reads especially must rest on *multiple weak signals
  agreeing*, not one. The output names the convergence; a lone signal lowers confidence.
- **Staleness is explicit.** Every image carries its capture date. A read off a stale image is
  framed as a **question to the owner**, never a claim. The owner's answer becomes better data
  than any image.
- **General principle vs. specific claim** (anti_hallucination §5): "weak signage hurts walk-in
  retail" is a general principle and may be stated; "*your* sign is hard to read" is a specific
  claim and requires a clear, current image or it is suppressed.

---

## 3. Data sources (resolved)

### Imagery
Priority order, all hedged and **source-labeled** (the source changes how much weight a read carries):

1. **Google Street View** — primary EXTERIOR source (signage, frontage, streetscape, dead-mall
   context). Use the **metadata endpoint** to read capture date + confirm a pano exists at the
   coordinates *before* pulling an image. Best coverage of physical locations; freshness varies
   (1–2 yrs metro, 3–7+ yrs rural) — hence the staleness rule.
2. **Google Business Profile / Maps photos** — interior + exterior; identity is tied to the
   listing, so the match is reliable. Often the richest single source for a given SMB.
3. **The business's own website** — best identity match; weight as **self-presentation, not
   ground truth** (owners post flattering shots). Often the only interior shots that exist.
4. **The business's Facebook page** — same posture as website.

**Dropped imagery sources (do not reintroduce):**
- **Foursquare** — only user check-in photos; stale, hospitality-skewed, thin for B2B and exactly
  the struggling businesses we'd care about. Better coverage from Google.
- **Yelp photos** — terms restrict *derivative use* (sending a photo to a model to assess it is
  derivative use whether or not we store the file). "Read but don't store" lowers but does not
  clear the risk. Yelp *review text*, if already obtained through legitimate means, may be used
  as context; Yelp photos may not be a pillar of this skill. **Legal-review item before launch.**

> Imagery legal note: confirm Google's terms cover **programmatic, at-request-time vision
> analysis** before launch. Posture is workable but this is a check-with-legal item, not a blocker.

### Nearby-business data (Module 2)
- **Google Places = vitality primary.** Returns `business_status`
  (`OPERATIONAL` / `CLOSED_TEMPORARILY` / `CLOSED_PERMANENTLY`) — the vacancy/dead-mall signal no
  other provider exposes cleanly. Nearby Search anchors on lat/long + radius, filters by place
  type, returns status. Pairs with the Google imagery above.
- **Mapbox = keep its existing §11.9 role** (geocoding + nearby same-classifier competitor +
  pricing lookup). Its Search Box API is a search/autocomplete product and does NOT expose
  reliable per-business open/closed status, so it cannot own vitality.
- **Cross-provider fallback only where coverage is thin** (sparse/rural). Do not always query both
  to "maximize coverage" — it adds cost and dedupe/taxonomy reconciliation for little gain.

---

## 4. Module 1 — Business Presentation (two-pass: describe, then judge fit)

**Question:** does what we can see of this business *match what a business of its type and
positioning is trying to be*? Not "is this storefront nice in the abstract" — a bare-bones taqueria
and a luxury salon are held to *their own* standard. The judgment is **fit to positioning**, and a
meaningful **mismatch** is the signal. Aligned presentation = silence.

This runs as **two passes**, deliberately separated so the seeing is exhaustive and the judging is
fair.

### 4.1 Pass 1 — Exhaustive visual description (Fable 5). Describe, do not grade.
Fable's ONLY job in this pass is to see thoroughly and report richly. It assigns no good/bad, makes
no fit judgment. Three rules force thoroughness:

**(a) Attributes, not nouns.** A bare inventory ("a sign and a bench are visible") is a failure.
Every element must be reported with its *qualities*: condition, age/wear, upkeep, color, legibility,
placement, and how it reads to a passerby. "A weathered wooden bench, paint peeling, one slat
broken, positioned half-blocking the entrance" — not "a bench is visible." If an element is named
without its attributes, the description is incomplete.

**(b) Zone sweep — cover every region, never skip.** Walk through fixed zones and report on each
(including an explicit "not visible / can't assess" where the image doesn't show it — never skip
silently):
- **Signage** — present? how many? size, mounting height, legibility at storefront distance,
  obstruction, condition, lit/unlit.
- **Windows / glass** — clean, cracked, papered-over, displays, visibility into interior.
- **Entrance / door** — obvious or hidden, condition, accessibility, open/inviting vs. closed-off.
- **Façade / walls** — material, upkeep, paint, damage, graffiti, dated vs. maintained.
- **Lighting** — exterior lighting present/working; (interior) bright/dim/uneven.
- **Ground / sidewalk / immediate frontage** — clean, litter, cracks, what occupies the frontage
  (tables, garage, blank wall).
- **Interior (only if an interior image exists)** — lighting, floor/wall/fixture condition, wear,
  clutter, dated vs. current, how full/sparse it reads.
- **In-frame neighboring context** — what's immediately adjacent (active shop, vacant unit, garage).

**(c) Honest about coverage.** Thoroughness is bounded by what the imagery contains. A single
straight-on shot can't show the side of the building or the interior — say so. Report what each
available image (and its source + capture date) does and does not reveal. The multi-source pull
(Street View + the business's own photos + GBP) exists to give more angles to describe; where
coverage is thin, the gap is reported, never guessed.

**Pass 1 self-suppression still applies:** if an image is obstructed, wrong-angle, dark, too low-res
to describe, or shows a different business, that image yields no description (and says why) rather
than a fabricated one.

### 4.2 Pass 2 — Fit-to-positioning judgment (Opus). Mismatch-only, hedged.
Opus takes Pass 1's rich description + the **positioning anchor** (below) and asks one question:
*does the observed presentation match what this business is positioned to be?* It flags only a
**meaningful gap** — and aligned presentation produces no flag at all (no manufactured concerns).

**The positioning anchor (the yardstick) — ratified rule:**
- **Use the owner's stated positioning / price-tier** (from the profile) **if the owner actively
  set or overrode it.** Owner-stated wins.
- **Otherwise use the classifier's inferred positioning / tier.** An inference the owner left
  standing is treated as tacitly accepted (consistent with profile data-precedence).
- When operating on the classifier inference (no owner statement), **hedge harder** — the
  expectation is softer, so the mismatch flag must carry lower confidence.

**Guardrails on "expected presentation" (so this doesn't become aesthetic police):**
- The expectation is **loose and tied to the business's own claimed positioning**, never a
  stereotype of the category. A successful dive bar's worn look may BE the brand — do not flag a
  mismatch just because a model thinks a "bar" should look polished.
- A mismatch is a **hypothesis, not a verdict** — surfaced to the owner to confirm, never asserted.
- Flag only where there's a **real, defensible gap** ("positioned as premium at this price point,
  but no visible signage and a worn interior — that gap may undercut walk-in trust"). If
  presentation roughly fits positioning, say nothing.
- The fairness contract (§7) fully applies: the flag is grounded in *observable presentation
  facts vs. stated positioning*, never in anything about the area's people or socioeconomics.

### 4.3 Operational-model gating
Apply only what's business-relevant, using classifier `operational_model`. A mobile food truck has
no fixed storefront; a B2B wholesaler's curb appeal is near-irrelevant; a pure-online business may
have no meaningful physical presence to assess. Mark non-applicable zones `not_applicable`, not
`null`, and never flag a business for lacking something its model doesn't need.

### 4.4 Output
Pass 1: a structured, attribute-rich description per zone, per image, with `source` +
`image_capture_date` + coverage notes. Pass 2: zero or more **fit flags**, each with the observed
facts it rests on (`basis`), the positioning anchor used (owner-stated vs. classifier-inferred),
`confidence`, and an `owner_confirmation_prompt`. No fit flag without a basis in Pass 1's
description. Aligned presentation → empty flags array.

---

## 5. Module 2 — Location Vitality

**Question:** Is this a lively, viable spot, or a quiet/declining one?

This is the module that cracks the Manhattan case (a lively 5-restaurant block vs. a dead
garage-lined block one street over). It runs on **convergent spatial + visual signals**:

### 5.1 Active-POI density — counted as data, judged as "normal for THIS business"
Two parts: a hard count (data), then a judgment of whether that count is normal *for this kind of
business in this kind of area* (reasoned from classifier output — no hardcoded thresholds).

**The count (data, backend):** anchor on the business's lat/long. Query Google Places Nearby Search
at a radius scaled to the area's density, **filtered to consumer-facing categories** (food, bars,
retail, entertainment, walk-in services) — NOT banks/back-offices, garages, service doors,
residential lobbies. Radius scales to context (dense-urban ~100–150m ≈ a block; suburban ~400–800m;
rural ~1mi+), derived from classifier `urban_density` / `geographic_context`. Return the count of
active consumer-facing POIs + the active/closed ratio (§5.2). These are facts.

**The judgment (reasoned, not thresholded):** do NOT apply a fixed "N+ = lively" rule — a count
that means "lively" on a Manhattan block means "dead" on a suburban strip and is meaningless rurally.
Instead, the agent reasons from the classifier output what density is *reasonable for this business
type and area*: a dense-urban walk-in café *should* sit among many active consumer POIs, so a near-
empty block is a real signal; a rural farm-supply store is *expected* to stand relatively alone, so
low surrounding density is normal and NOT a concern. The classifier tells the agent what "normal"
looks like here; the count tells it where reality sits relative to that. The output is "thin / normal
/ dense **for this kind of business in this kind of area**," never a context-free number-to-label
mapping.

*(This mirrors the Module 1 anchor logic: the classifier supplies the expectation; the observed
data is judged against it, not against a universal scale. It leans on the model's world-knowledge of
what a given business type's surroundings should look like — kept honest by the real counts and the
owner-confirm step.)*

### 5.2 Active-vs-closed ratio (the dead-mall / decline signal)
Within the same radius, compute the ratio of `OPERATIONAL` to `CLOSED_PERMANENTLY` consumer POIs.
A ring of permanently-closed pins is a strong declining-corridor / dead-mall signal.

### 5.3 Active-frontage read (the "quiet block" refinement)
"Quiet" is not "low-end" — it is **absence of active consumer frontage**: garage entrances,
service doors, blank walls, parking structures, residential lobbies. Detected two ways that must
agree: (a) near-zero consumer POIs at small radius, and (b) Street View showing garage doors /
blank façades rather than shopfronts and signage. The *absence* is the signal.

### 5.4 Anchor-tenant logic (malls specifically)
For mall/shopping-center locations: is there still an **active anchor** (department store, grocery,
cinema) nearby, or did it close (`CLOSED_PERMANENTLY`)? A dead anchor is the classic dead-mall tell.

### 5.5 Street View corroboration
The vision model views the streetscape to confirm or contradict what the spatial data implies. If
the data says "lively" but the image shows a shuttered street (or vice versa), that *tension*
lowers confidence and is itself surfaced — never silently resolved in favor of one source.

### 5.6 Reviews (opportunistic only)
Customer reviews on the business occasionally name a location problem ("dead mall, empty lot,"
"impossible parking," "can't find it, no sign"). Use these if present as a corroborating signal.
**Do NOT treat as load-bearing** — nobody reviews the empty mall itself, so absence of complaint
is not evidence of vitality.

**Output:** an overall vitality read (`lively` / `moderate` / `quiet` / `declining`) plus the
named convergent signals, each with its basis, and an explicit `signal_agreement` note (do the
spatial and visual signals agree?). Thin or conflicting signals → lower confidence, and a read
may be suppressed entirely.

---

## 6. Why we do NOT classify specific competitors

We deeply classify *our own user* (their QBO, POS, profile answers, observations). We have none of
that for the business across the street. A POI feed only tells us "Mexican Restaurant, 0.4mi" — it
cannot tell a $6 hole-in-the-wall from a $22 sit-down, which is exactly the granularity that
decides whether they actually compete. So:
- **Permitted:** coarse competitor **density** as a context signal ("you're in a dense taco market").
- **Forbidden:** naming + classifying specific external businesses as confirmed competitors — that
  is false precision the data can't support.
- The §11.9 Mapbox competitor-pricing work is separate and stays as-is; it is not extended by this skill.

---

## 7. The Fairness Contract (non-negotiable)

Visual/location assessment can quietly encode bias. This contract is load-bearing.

- **Assess only observable, business-operations-relevant factors:** signage legibility, exterior
  upkeep, interior lighting/cleanliness/dating, active vs. dead frontage, neighboring vacancies,
  accessibility, parking, visibility.
- **Never** infer or state anything about the people in an area, the socioeconomic character of a
  neighborhood, "good/bad part of town" as a social judgment, demographics, safety-by-implication,
  or any protected-class-adjacent characteristic. "Bad part of town" is reframed strictly as
  observable business factors (e.g., "several neighboring units are permanently closed and the
  block shows little active retail frontage"), never as a judgment about who is there.
- If a read can only be expressed as a social/demographic judgment, **suppress it.**
- Owner-facing language stays about *the business's situation and options*, not about the area's
  worth or its residents.

---

## 8. Output schema (learnings, per M&D write schema)

Findings are written as memory learnings (not profile fields, not outputs). Illustrative shape:

```json
{
  "skill": "physical_presence_location_vitality",
  "location_id": "loc_dauphin_st",
  "positioning_anchor": {
    "source": "owner_stated",   // owner_stated | classifier_inferred
    "value": "premium full-service salon, top price tier"
  },
  "module_1_presentation": {
    "pass1_description": {
      "exterior": {
        "signage": "One small backlit sign, ~18in, mounted low and partially obscured by an awning; legible only within ~20ft; weathered with one dim bulb.",
        "windows_glass": "Front glass clean; no display; interior not visible through tint.",
        "entrance": "Single glass door, unmarked, set back under a dim overhang; not obviously the main entrance.",
        "facade_walls": "Painted stucco, faded, hairline cracks near the base; no visible damage.",
        "lighting": "No working exterior accent lighting visible in a daytime image.",
        "ground_frontage": "Clean sidewalk; no seating or display; frontage is mostly blank wall to the left.",
        "neighboring_context": "Adjacent unit to the right appears vacant (papered windows).",
        "coverage_note": "Single straight-on Street View frame (2024-08); side of building and interior not shown."
      },
      "interior": "not_assessed — no interior image available"
    },
    "pass2_fit_flags": [
      {
        "flag": "Presentation may undercut premium positioning",
        "basis": "Positioned as a top-tier salon, but signage is small/obscured/weathered, the entrance is unmarked and dim, and the facade is faded — Pass 1 exterior description.",
        "anchor_used": "owner_stated",
        "confidence": "moderate",
        "owner_confirmation_prompt": "Your salon is positioned as premium, but the storefront in our imagery (2024) reads as understated — small, weathered signage and an unmarked entrance. Does that match the impression you want walk-ins to get?"
      }
    ]
  },
  "module_2_vitality": {
    "overall": "quiet_for_context",
    "confidence": "moderate",
    "context_note": "Judged against a dense-urban walk-in business, which would normally sit among many active consumer POIs.",
    "signal_agreement": "spatial and visual signals agree",
    "signals": [
      { "type": "active_poi_density", "value": "2 active consumer POIs within 150m — thin for a dense-urban walk-in business",
        "basis": "Google Places Nearby Search, type-filtered, 150m radius; classifier urban_density = dense-urban", "source": "google_places" },
      { "type": "active_frontage", "value": "Street-level is mostly garage entrances and blank wall",
        "basis": "Street View shows garage doors and no shopfronts", "source": "street_view",
        "image_capture_date": "2023-05" }
    ]
  },
  "owner_confirmation_prompts": [
    "Your block looked fairly quiet in the imagery we have (from 2023) — does that match your day-to-day, or has it changed?"
  ]
}
```

Key schema rules: **Pass 1 is pure description** (attributes not nouns, every zone, coverage noted);
**Pass 2 fit flags are mismatch-only** and each carries its `basis` (pointing back to Pass 1), the
`anchor_used` (owner_stated vs. classifier_inferred), and an `owner_confirmation_prompt`. Aligned
presentation → empty `pass2_fit_flags`. Module 2's `overall` is always framed *for context*, never a
context-free label. Suppressed reads are explicit; stale-image reads generate confirmation prompts;
nothing here is a hard profile fact (it's longitudinal, owner-correctable knowledge).

---

## 8.5. Execution flow (modeled on DIA's trigger/batch pattern)

How the enrichment agent actually runs. Mirrors DIA: async, on-event, dual-backend, not on the
synchronous refresh cycle.

**Trigger:** runs after the Classifier completes for a business (so its output is available),
at **onboarding**, and on the **cadence** decided in §10. One job per `location_id` (multi-location
businesses enqueue one job per active location — binds to `multi_location_handling.md`).

**Step sequence (per location):**
1. **Geocode** the location address → lat/long (Mapbox, already in stack). Skip if `locations[]`
   already carries coordinates.
2. **Spatial pull (pure backend code, no model):** Google Places Nearby Search at the
   density-scaled radius (§5.1), type-filtered to consumer-facing categories, with
   `business_status` in the field mask. Compute the active count + active/closed ratio (§5.2).
3. **Image pull (pure backend code):** Street View Static + metadata (capture date, pano exists?);
   GBP/website/Facebook photos where available. Attach `source` + `capture_date` to each.
4. **Vision read — Fable 5:** each image → structured per-item reads with self-assessed confidence
   and suppression (§4, §5.3, §5.5). `claude-fable-5`, base64 image input, the skill's rubric in
   the system prompt.
5. **Fusion — Opus:** combine the spatial math + vision reads + (opportunistic) review signals
   into the hedged Module 1 / Module 2 output (§8), applying convergence (§2), the fairness
   contract (§7), and the Classifier-deconfliction rule (§8.7). `claude-opus-4-8`.
6. **Write learnings** to the customer's Memory namespace (§8.6); dreaming promotes durable ones.

**Why dual-backend, like DIA:** Fable only where there's something to *see* (step 4). Everything
else is cheaper/correct on Opus or is plain code. Same cost-control logic DIA documents.

**Fable retention + reroute notes (carried from DIA):** Fable's 30-day operational retention (tied
to its safety classifiers) applies to the imagery sent in step 4 — the same ZDR conversation that
covers DIA's lease/insurance docs covers this (storefront imagery is far less sensitive, same
regime). Fable's cyber/bio/chem auto-reroute to Opus won't trip on storefront photos — non-issue,
same as DIA.

---

## 8.6. Memory write + re-run supersession

- **Write path / schema:** per the M&D write schema (§7 of M&D spec). `observation_type`:
  `pattern` for vitality/presentation reads (they're interpretive context, not a single metric),
  with the per-signal `basis` preserved. Path uses the enrichment **job ID** wherever the schema
  expects `{session_id}` (same convention DIA uses for upload jobs — these don't run in a live
  session).
- **NOT a profile field.** Unlike DIA (which writes hard profile facts), this writes **learnings
  only**. Presentation/vitality is longitudinal, hedged, owner-correctable — it does not belong in
  a structured profile field. (Exception: once an owner *confirms* a read, that confirmed fact may
  graduate to durable memory/profile truth — §9.)
- **Re-run supersession (mirrors DIA's document-replace logic):** when the agent re-runs on
  cadence and produces an updated read for a location, the prior read is marked
  `superseded_by`/`outdated: true` — **not deleted** — so year-over-year change is visible ("this
  block has gotten quieter since last year" is itself a signal). Supersession keys on
  `location_id` + module.
- **Org playbook:** per-customer only. Never writes to `/memories/org_playbook/` (same permission
  rule as DIA).

---

## 8.7. Graceful degradation + the Classifier-deconfliction seam

**No data = no claim (graceful degradation).** Coverage gaps are normal (rural addresses, brand-new
locations, no Street View pano, no photos, sparse POIs). The agent must degrade, never fabricate:
- No usable imagery → Module 1 reads are `suppressed`; no presentation claim is made.
- No/sparse POI data → Module 2 confidence drops or the read is suppressed; never assert vitality
  from a thin set.
- Total absence (no images AND no POI data) → the agent writes **nothing** for that location (or a
  single learning noting coverage was insufficient). A null result is a correct, safe outcome — it
  is never filled with a guess.

**Classifier-deconfliction seam (RESOLVED — D4: no field edit, source of truth reconciles).** The
Classifier already emits qualitative geographic prose today (e.g., "foot traffic moderate, peaks
during festival weekends") — a *guess* from web research. This agent produces an *evidence-backed*
read from imagery + POI data. The two do not contend over a field: **the 9th agent writes its read
into the Memory layer like every other agent; dreaming promotes it into the living summary, which is
authoritative.** When the measured read and the Classifier's guess disagree, the living summary's
measured read wins **at read time** — `classifier_output` is never edited. This keeps each agent's
output its own and avoids a parallel source of truth (the same reasoning that killed the 3 simple
tag dimensions). The agent's own re-runs supersede each other per §8.6.

**The one dependency this rests on:** downstream agents must treat the living summary as
authoritative over a stale `classifier_output.geographic_context` value when they disagree. If
that's already how reads work, no new mechanism is needed. If any consumer reads `geographic_context`
straight from the JSON without consulting the summary, that consumer is the thing to fix (prefer the
summary) — a read-side fix, never one agent writing into another's output. Naveen to confirm.

---

## 9. Owner-facing surfacing (RESOLVED — D3: Business Health → Priority Watch Areas)

- **Home:** location-vitality and presentation reads surface in the **Business Health tab's
  Priority Watch Areas** section. That section is explicitly the home for "AI proactive observation
  of a developing pattern, below hard threshold" — which is exactly what a hedged vitality read is.
  Not a new category card (those are score+glow only, no room for a hedged observation), not its own
  section, not the Active Health Alerts surface (those are deterministic threshold crossings).
- **Confirm/correct:** rendered with an owner confirm/correct affordance. A confirmed read graduates
  to durable truth (and the hedging drops); a corrected/dismissed read is suppressed and recorded.
- **Never** asserted as fact. Always hedged, low-weight, dismissable.
- **Voice:** "We noticed your signage may be hard to spot from the road — does that match your
  experience?" — not "Your storefront is hurting you."
- **Dependencies (see §10):** this requires a Business Health spec edit (Priority Watch Areas must
  accept these learnings as an eligible input + gain the confirm/correct control) and an Orchestrator
  HEALTH NARRATIVE MODE edit (the Orchestrator authors the BH narrative and must read these learnings
  from the living summary and emit them as a watch area). The 9th agent producing the learning is
  necessary but not sufficient — without those two edits, nothing renders.
- **Other tabs:** may still pick up the read via the living summary if relevant (e.g., FA on the FO
  tab if it ever becomes financially pressing, Scenario Lab in a relocation what-if), but BH Priority
  Watch Areas is the guaranteed home.

---

## 10. Decisions (ratified June 10, 2026) & build items

### Ratified decisions
- **D1 — Executor: formal 9th agent.** Claude-native, no migration, DIA-parallel. Add to
  `Agent_Migration_Master_Tracker_v2.md` as agent #9.
- **D2 — Cadence: three triggers.** (a) onboarding (first run), (b) monthly refresh (catch
  staleness / area change → year-over-year vitality signal via §8.6 supersession), (c) on-new-imagery
  (owner uploads/adds new photos → re-run on the new material). Each re-run supersedes-but-retains
  the prior read.
- **D3 — Surfacing: Business Health → Priority Watch Areas**, as a low-weight, owner-confirmable
  watch area (NOT a new category card, NOT its own section — the Watch Areas surface already exists
  for soft signals, which is exactly what a hedged vitality read is). See §9 + the dependency note below.
- **D4 — Deconfliction: no field edit; the source of truth reconciles.** The 9th agent writes its
  measured read into the Memory layer like every other agent. Dreaming promotes it into the living
  summary, which is authoritative. When the measured read ("quiet") and the Classifier's
  web-research guess ("foot traffic moderate") disagree, the **living summary's measured read wins
  at read time** — nobody edits `classifier_output`. This keeps the Classifier's output its own and
  avoids a parallel-source-of-truth problem (consistent with why the 3 simple tag dimensions were
  killed). Supersession across the agent's own re-runs still applies (§8.6).
  - **One Naveen confirmation this depends on:** downstream agents must treat the living summary as
    authoritative over a stale `classifier_output.geographic_context` field when the two disagree.
    If that read-precedence is already how the system behaves, this needs no new mechanism. If any
    consumer reads `geographic_context` straight from the JSON and never consults the summary, that
    consumer needs to prefer the summary (or the field's freshness needs flagging) — a read-side
    fix, not an agent writing into another agent's output.

### Dependencies created by D3 (must be tracked)
- **Business Health spec edit:** Priority Watch Areas must (a) accept location-vitality/presentation
  learnings (sourced from the 9th agent via the living summary) as an **eligible input** — today
  watch areas are built from the scored signal payload, so this new source must be explicitly
  allowed; and (b) gain a **confirm/correct affordance** (watch areas today are display-and-explain;
  a vitality watch area needs an owner yes/that's-wrong control). Not a rewrite — two additions.
- **Orchestrator HEALTH NARRATIVE MODE edit:** the Orchestrator authors the BH narrative (not the
  FA). For a location-vitality watch area to render, HEALTH NARRATIVE MODE must read these learnings
  from the living summary and emit them as a watch area with the confirm/correct payload. This is an
  Orchestrator prompt touch, not just a UI change.

### Build items (Naveen)
- **B1 — Legal check (GATES LAUNCH):** Google Places + Street View + GBP photos terms for
  programmatic, at-request-time vision analysis. Yelp photos already excluded.
- **B2 — Provider wiring:** Google Places Nearby Search (type-filtered, radius-scaled,
  `business_status` in field mask) + Street View Static + metadata endpoint. Mapbox retained for
  §11.9 geocoding/competitor work + thin-area fallback.
- **B3 — 9th agent build:** thin system prompt (3 triggers, route Fable-for-vision /
  Opus-for-fusion, write learnings to Memory per D4 — no `classifier_output` edit), skill loaded
  inline (Option 1, Tracker §1G), async on-event. Roster entry in the Migration Tracker.
- **B4 — Radius-tier mapping:** confirm dense/suburban/rural thresholds against the actual
  `urban_density` / `geographic_context` values the Classifier emits today.
- **B5 — Memory wiring:** learnings write (observation_type `pattern`, job-ID as session_id),
  re-run supersession on `location_id` + module, dreaming promotion verified. Per-customer namespace
  only.
- **B6 — Graceful degradation (§8.7):** null/suppressed on missing imagery, sparse POI, total
  absence. No fabrication.
- **B7 — Cost envelope:** per-run Google Places + Street View + Fable budget; set a per-job cap.
- **B8 — Multi-location:** one job per active location; reads attributed by `location_id`
  (binds to `multi_location_handling.md`).
- **B9 — BH + Orchestrator edits:** the two dependency edits above. Sequence so the agent isn't
  producing learnings nothing renders.

### Correctly out of scope (not gaps — do not reopen without cause)
Paid foot-traffic panels; competitor identity/classification (§6); seasonality (owner's own POS);
Google Popular Times (no clean API); Foursquare and Yelp photos (§3).

"""