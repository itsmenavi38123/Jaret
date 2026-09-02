---
name: signal_lever_scenario_opportunity_definitions
description: Locked definitions of the LightSignal taxonomy — SIGNAL, LEVER, SCENARIO, OPPORTUNITY, WATCH AREA PATTERN — plus the five-criteria gate that determines whether something qualifies as an Opportunity. Authoritative source is Research Scout V3; consolidated here so every downstream agent (Scenario Lab, Orchestrator, FA, Opportunity Prep) uses the same boundary lines.
---

# Signal / Lever / Scenario / Opportunity Definitions

LightSignal's product vocabulary depends on five precisely-bounded terms. The Research Scout prompt holds the canonical "locked" definitions ("Do Not Violate"). Other agents use these terms throughout but rely on Scout's definitions implicitly. This skill consolidates the definitions so every agent classifies the same item the same way and so the boundaries between agents stay sharp.

These are the only authoritative meanings of these terms in LightSignal. Do not redefine. Do not soften. Do not collapse two into one for narrative convenience.

---

## SIGNAL

**Definition.** An internal or observed pattern about the business or its market.

**Properties.**
- Not searched on the web.
- Not returned as a card.
- Sourced from internal data (accounting, POS, reviews, behavioral patterns), classifier output, or the LightSignal scoring engine.

**Examples.** Late-night demand spike. Margin compression. Idle equipment capacity. DSO slipping. Repeat customer rate dropping. Crew turnover accelerating.

**Where signals come from in the pipeline.** Scoring engine, classifier `tier_b_signals_active`, behavioral pattern recognition system, owner state detection system, the Orchestrator's `signal_state` payload field.

---

## LEVER

**Definition.** An internal action the business controls in response to a signal.

**Properties.**
- Not searched on the web.
- Not returned as a card.
- Decided by the owner (sometimes with Scenario Lab modeling) and executed by the owner.

**Examples.** Raise prices. Adjust hours. Hire staff. Bundle inventory. Optimize pricing. Improve online reviews. Switch a vendor. Renegotiate a contract.

---

## SCENARIO

**Definition.** A strategic decision requiring financial modeling and analysis.

**Properties.**
- Not returned as a card — belongs in the Scenario Lab.
- Owner-facing decision that requires structured trade-off modeling: cost vs. revenue, risk vs. return, current state vs. projected state.
- Scenario Lab is the sole scenario evaluation engine.

**Examples.** Open a second location. Acquire a competitor. Take on new debt. Lease vs. buy equipment. Hire vs. expand commissary. Raise prices vs. cut costs.

**Where scenarios live.** Scenario Planning tab in the LightSignal platform. The Orchestrator routes scenario intents to the Scenario Planning tab; it never computes scenario KPIs, never forecasts scenario outcomes, never evaluates scenario risk itself.

---

## OPPORTUNITY

**Definition.** A real, external door involving a third party, with timing and a decision point.

**Properties.**
- Only opportunities are searched via web tools and returned as cards in OPPORTUNITY DISCOVERY mode.
- Always involves an external organization with control over access.

**Must pass the five-criteria gate** (see Section "The Five-Criteria Gate" below).

**Examples.** A festival vendor application. A government RFP. A grant application window. A pitch competition. A corporate supplier diversity application. A platform onboarding incentive with a deadline.

---

## WATCH AREA PATTERN

**Definition.** A business trend identified by the Orchestrator that needs investigation.

**Properties.**
- Investigated in Research Scout's Mode 2 (WATCH AREA INVESTIGATION).
- Not returned as opportunity cards.
- Outputs grounded possible causes from real-world sources (web search, weather, local events, competitor activity, market news).

**Examples.** Friday revenue declining 18% over 3 weeks. Acme Corp payment timing slipping from 28 to 51 days. Avocado costs from Sysco spiked to $49/case.

**Distinction from SIGNAL.** A signal is the observed pattern itself ("Friday revenue is declining"). A watch area pattern is what the Orchestrator hands to Scout as a packaged investigation request ("investigate why Friday revenue is declining"). The same underlying pattern becomes a watch area when external research is needed to explain it.

---

## The Five-Criteria Gate (Opportunity qualification)

Before any candidate becomes an opportunity card, it must pass ALL FIVE criteria. If any single criterion fails, discard the candidate entirely. Do not create a card with a low score — exclude it completely.

1. **A third party controls access to it.** An external organization owns or governs this opportunity. The business cannot simply decide to participate — they must apply, register, bid, or be accepted. There is a real gatekeeper.

2. **There is a specific window to act.** A deadline, application period, event date, or enrollment window exists. The opportunity is not permanently available. Missing the window means waiting for the next occurrence or losing access entirely.

3. **The business must do something deliberate to participate.** Active participation is required — submitting an application, registering as a vendor, placing a bid, pitching to a buyer, entering a competition. Passive eligibility does not qualify.

4. **There is a definable cost of participation.** A real cost exists, even if that cost is primarily time and preparation effort. Booth fees, application materials, bid preparation, sample production, registration fees, or matching fund requirements all count.

5. **There is a direct revenue or capital outcome if participation succeeds.** Success produces a direct financial result — event sales revenue, a grant award, a contract win, a prize payout, or a placement relationship that generates orders. Indirect outcomes like brand awareness, networking, or press coverage do not qualify on their own.

---

## Common Exclusion Cases (fail the gate immediately)

Use this list when classifying an ambiguous candidate. Each is paired with its correct classification.

| Candidate | Why it fails the gate | Correct classification |
|-----------|------------------------|------------------------|
| "Raise prices" | No third party, no window, no direct outcome | Lever |
| "Hire a new employee" | Entirely internal | Lever |
| "Open a second location" | Strategic modeling decision | Scenario |
| "Attend a networking event" | No direct revenue outcome | Excluded unless actively selling as registered vendor |
| "Get listed on DoorDash/Etsy" | Platform always open, no defined window | Excluded. Time-limited onboarding incentive with deadline qualifies. |
| "Improve Google reviews" | Entirely internal | Lever |
| "Partner with another business" | No formal application window, revenue not definable upfront | Lever or Scenario depending on structure |
| "Get a business loan" | Always available, no application window | Excluded. Specific CDFI/SBA round with defined funding pool and deadline qualifies. |
| "Apply for press or media coverage" | Indirect outcome, no direct revenue, no third party controlling access | Lever |
| "Optimize pricing or menu" | Entirely internal analysis | Lever |

---

## Boundary cases the prompts call out

- **Recurring events.** Weekly markets, monthly pop-ups → surface as one card per occurrence with a unique `start_date`. Do not collapse recurring events into a single evergreen listing.
- **Vacant storefront available for lease.** Not a venue residency. That is a second-location scenario. A venue residency has controlled access, defined slots, an application process, and a term limit.
- **Whole Foods accepts local supplier applications** (no window) → not an opportunity. **Whole Foods Local Producer Loan Program applications open April 1–May 15** → opportunity.
- **Certifications already held.** Do not re-surface a certification the business already holds. But if a relevant set-aside RFP exists alongside a certification the business doesn't hold, surface both with a visible prerequisite link between them.
- **Accelerator without capital component.** Pure mentorship without a cash stipend, equity investment, grant, or direct capital component does not qualify.

---

## How These Definitions Constrain Each Agent

| Agent | Constraint |
|-------|------------|
| **Research Scout** (Mode 1 — Opportunity Discovery) | Only searches for and returns OPPORTUNITIES. Levers, scenarios, signals — never surfaced as cards. |
| **Research Scout** (Mode 2 — Watch Area Investigation) | Takes a WATCH AREA PATTERN from the Orchestrator and returns grounded possible causes. Does not score, does not recommend actions, does not return opportunity cards. |
| **Orchestrator** | Routes scenario intents to Scenario Lab (does not evaluate scenarios itself). Coordinates with Scout for opportunities and watch areas. Authors Business Health narrative directly. |
| **Scenario Lab** | Owns SCENARIO evaluation. Owner-facing decision modeling. Does not produce LEVERS (those are owner actions the scenario informs) and does not return OPPORTUNITY cards. |
| **Financial Analyst** | Explains computed metrics and assists across modes. Does not produce opportunity cards. Its SCENARIO MODE is parallel to Scenario Lab and may be dead code (noted in the FA prompt itself). |
| **Opportunity Prep Agent** | Produces preparation checklists, judgment prompts, and checkpoint summaries for OPPORTUNITIES the owner is preparing for. Does not evaluate whether to proceed — that is the owner's decision. |

---

## Reconciliation notes

- Research Scout is the canonical source. The other prompts (Scenario Lab, Orchestrator, FA, Opportunity Prep) use these terms throughout without redefining, which is why consolidation matters: the definitions live in one place and the other agents inherit them.
- No contradictions surfaced across the source prompts. Scenario Lab uses "Scenario" exactly the way Scout defines it. Orchestrator's "watch areas" are Scout's "watch area patterns". FA's "Opportunity" in OPPORTUNITY WHY SUGGESTED MODE points to the same Scout-curated opportunity cards.
- The Five-Criteria Gate is a Scout-only concept; downstream agents trust that any opportunity in the payload has already passed the gate. The gate definition is reproduced here so downstream agents can recognize when something the owner is referring to in chat would not have passed the gate (e.g., owner says "let me get listed on Etsy" — that's not an opportunity, even though it sounds like one).
