---
name: multi_location_handling
description: How LightSignal agents read the locations[] array, determine whether a scenario or analysis is location-specific vs. business-wide, scope financial math accordingly, and research multi-location businesses without collapsing distinct markets. Combines multi-location rules added May 2026 to the Scenario Lab v1.3 and Classifier V4.1 prompts.
---

# Multi-Location Handling

This skill consolidates the May 2026 multi-location-awareness rules that were added in parallel to the Scenario Planning Lab v1.3 prompt (Step 1 "Reading the locations[] Array", Step 5 "MULTI-LOCATION SCOPING RULE", Step 7 verdict-line guidance, and three additions to the "What You Never Do" list) and to the Business Profile Classifier V4.1 prompt (GEOGRAPHIC GRANULARITY RULE multi-location expansion, geographic_context and operational_model dimension guidance, TAGS LAYER multi-location handling, ANTI-HALLUCINATION rule against assuming single-location, and the WEB SEARCH multi-location pattern).

All rules below are preserved from those source prompts. No new rules are introduced.

---

## 1. The `locations[]` Array — Schema

The business profile contains a `locations[]` array in Section 1 Business Basics. Each entry has these fields:

- `name`
- `address`
- `city`
- `state`
- `postal_code`
- `lat`
- `lng`
- `neighborhood`
- `space_type`
- `role` — one of: `headquarters`, `flagship`, `satellite`, `popup`, `seasonal`, `other`, or blank
- `opened_date`
- `status` — one of: `active`, `paused`, `closing`

Per-location revenue/expense data may also be available in connector data, tagged via QBO Class/Location or POS location fields. Use it when present.

The `hq_location` field is deprecated. Never reference it as a standalone field — always read from `locations[]` and use the `headquarters` or `flagship` role (or first active location by `opened_date` as fallback).

---

## 2. Scoping Rule — Location-Specific vs. Business-Wide

Before running any scenario, analysis, or math, determine whether the work is location-specific or business-wide.

### LOCATION-SPECIFIC indicators

- The owner names a specific location (by name, neighborhood, or address).
- The owner mentions geography that matches one location and not others (e.g., "the Spring Hill spot", "the downtown food truck", "our Williamsburg store").
- The scenario inherently applies to one location only (e.g., "competitor opening across the street from our Dauphin Street location", "roof leak at the Spring Hill site").

### BUSINESS-WIDE indicators

- The owner asks about the business overall (e.g., "can I afford to take a salary increase", "should I hire two more people").
- The scenario applies to the company as a whole (e.g., "a recession hits", "we raise prices across the board").
- The owner does not reference any specific location.

### Special cases

- If the business has only one active entry in `locations[]`, every scenario defaults to that location implicitly. No scoping question is needed.
- If the business has multiple active locations and the scenario is ambiguous, ask one clarifying question before running:

  > "Does this affect one location specifically or your operation overall? If one location, which?"

- Use the `headquarters` or `flagship` role as the primary reference point when the scenario is business-wide but needs an anchor (peer benchmarks, market context, local economic conditions). If no role is set, use the first active location by `opened_date`.
- If the scenario is AMBIGUOUS and you did not ask a clarifying question: default to the most likely scope based on the question wording, state the scope assumption explicitly in the verdict, and offer the owner the ability to rerun scoped differently in the closing line.

---

## 3. Financial Math Scoping (Scenario Lab — Step 5)

Apply the scope determination before doing any math.

### If LOCATION-SPECIFIC

- Scope revenue, cost, and cash impact calculations to the affected location only.
- Use per-location revenue if available in accounting/POS data (QBO Class/Location tagging or POS location data).
- If per-location revenue is not available, estimate the affected location's share based on stated or implied weight (e.g., "Dauphin Street is our main location, represents about 70% of revenue per the owner") and label this as an estimated assumption.
- The impact you calculate affects only that location's contribution to the overall business — do not aggregate.
- In the output, reference the location by name throughout.
- Identify whether spillover to other locations is plausible (foot traffic shifts, customer migration) and flag separately if material.

### If BUSINESS-WIDE

- Aggregate impact across all active locations.
- Use the consolidated revenue/cost figures from accounting and profile.
- In the output, reference "your business overall" or list locations by name where relevant.
- If different locations would experience the same scenario differently (e.g., a regulation that only applies to some states), call out the per-location variance explicitly.

### Reserve floor check (cash is business-level)

Cash is a business-level metric, not a per-location metric. Even for location-specific scenarios, the reserve floor check applies to overall business cash. A location-specific revenue hit still feeds through to overall cash position.

### Sanity check addition

When sanity-checking results, verify: for location-specific scenarios, that you did not inadvertently use consolidated business-wide figures for what should be location-only math.

---

## 4. Geographic Research Rule (Classifier V4.1 — Geographic Granularity Rule)

When the business profile's `locations[]` array contains more than one active location, treat each location as a separate geographic anchor for research purposes. Do NOT collapse to a single "primary location" geography or average across locations.

Specifically:

- Run geographic-context searches for each active location separately (city + neighborhood combination).
- Run competitive-landscape searches around each location's address separately.
- If two locations share a neighborhood or city block, you may research them together to save budget.
- If locations are in different cities or different markets, research each market independently. A business with one location in downtown Mobile and one in Spring Hill faces two distinct competitive landscapes, two distinct foot traffic patterns, two distinct demographic profiles.

The output should capture each location's distinct context where it materially differs.

### Web search budget allocation

For multi-location businesses, the search budget allocates research to each location's specific market rather than concentrating on one.

---

## 5. Dimension Guidance for Multi-Location Output (Classifier V4.1)

### `operational_model` dimension

When multi-location is selected, do not just say "multi-location" — describe the structure. Specify the count and how the locations relate.

Read the `locations[]` array — pull location count, location names, role (`headquarters`/`flagship`/`satellite`/`popup`/`seasonal`), and status (`active`/`paused`/`closing`) directly from it.

Examples of good multi-location `operational_model` output:

- "Two-location operation: flagship counter-service taco restaurant in downtown Mobile (Dauphin Street, opened 2022) plus satellite truck rotating through Spring Hill office parks (added 2024). Owner runs flagship daily; satellite has a dedicated operator."
- "Three-location service business: headquarters in downtown Atlanta (admin and primary service area), plus two satellite offices in Buckhead and Marietta. Manager-led at each location; owner travels between weekly."
- "Multi-state retail operator: 4 brick-and-mortar locations across Mobile, Pensacola, and Gulfport. Mixed ownership (owner runs Mobile location daily; manager-led at the other 3)."

### `geographic_context` dimension

For multi-location businesses, describe each location's context distinctly where they materially differ. When two locations share market characteristics (same neighborhood, same city block), you may unify the description with a note that both share context.

Examples — same-market locations (may unify):

- "Operates across downtown Mobile, AL — both locations sit within the same tourist-adjacent commercial district with overlapping foot traffic patterns. Gulf Coast hurricane exposure annually June-November affects both equally."

Examples — different-market locations (describe distinctly):

- "Two distinct market contexts. Dauphin Street location: downtown Mobile, AL tourist-adjacent commercial district with lunch-hour office traffic and festival weekend peaks. Spring Hill location: Mobile suburban office park corridor, weekday-only office worker base, no weekend traffic. The two locations face different demand patterns and different competitive landscapes."
- "Multi-market retail across Mobile, Pensacola, and Gulfport. Each market has distinct seasonality (Pensacola tourist-heavy spring, Mobile event-driven year-round, Gulfport casino-spillover Friday-Sunday) and different competitive intensity."

### `competitive_position` dimension

For multi-location businesses, capture per-location competitive context where it materially differs. Example:

- "Mobile flagship: strong neighborhood differentiation as the only fish-taco-focused concept in downtown Mobile; closest direct competitor 6 blocks away (Coastal Bites, opened October 2025). Spring Hill satellite: more contested — 4 similar quick-service concepts within 0.5 miles in the same office park corridor."

### `additional_dimensions` — `location_strategy` (optional)

For multi-location operators, an optional `location_strategy` additional dimension is available (e.g., "flagship-and-satellites", "co-equal multi-market", "hub-and-spoke service"). Use when the multi-location relationship has strategic distinctiveness beyond what `operational_model` captures.

### Sparse-data flag for multi-location

Acceptable sparse-data flag example:

- "multi-location business but per-location revenue mix not available in connector data — locations weighted equally for analysis"

---

## 6. Tags Layer Multi-Location Handling (Classifier V4.1)

For multi-location businesses, include a neighborhood AND city tag for each active location, plus a structural tag describing the multi-location pattern (e.g., `two_location`, `three_location`, `multi_market`, `flagship_plus_satellite`, `hub_and_spoke`).

Do not lose location signal by tagging only the primary location.

Example (multi-location restaurant):

```
["fast_casual", "mexican_taco_concept", "two_location",
 "flagship_plus_satellite", "owner_operator", "downtown_mobile",
 "spring_hill_mobile", "mobile_al", "gulf_coast", "growth_stage",
 "mid_price_tier", "b2c_local"]
```

Note: `multi-location is NOT the same as hybrid`. A business with three locations all running the same model is multi-location, not hybrid. `is_hybrid` is about multiple business models; multi-location is about multiple physical (or virtual) presences executing the same or different models. A business can be both.

---

## 7. Verdict-Line and Output Guidance (Scenario Lab — Step 7 and related sections)

When a scenario is location-specific, name the location explicitly throughout the output:

- **Verdict sentence**: "A competitor opening on Government Street typically takes 12-18% of foot traffic from your Dauphin Street location in the first 6 months, representing ~$3,200/month in revenue at risk from that location specifically."
- **Key Numbers**: Label any number that applies only to the affected location to make the scope clear (e.g., "Dauphin Street monthly revenue impact" not just "monthly revenue impact").
- **Assumptions table**: Make clear which numbers are per-location vs. business-wide.
- **Steps to Take — HOW**: Reference the affected location's specific market — its neighborhood, foot traffic patterns, local vendors and contacts.
- **Things to Keep in Mind**: For multi-location businesses, this is a good place to flag spillover effects — how the affected location's outcomes might reach other locations (customer migration, brand perception, staff reallocation pressure).
- **Peer Context**: For location-specific scenarios, ground peer context in the affected location's market specifically.
- **Alternatives**: For multi-location businesses, one valid alternative format is "do this at location A only, not B" or "phase across locations" — surface this when it's a realistic alternative.
- **Chart Data**: For location-specific scenarios, label the series name to include the location (e.g., "Dauphin Street Projected Cash Balance") so the chart visually reflects the scope.
- **Closing line addition**: For location-specific scenarios where the owner has multiple locations, append:

  > "Want me to rerun this for your other location(s) as well, or compare across them?"

### Follow-up (Type 2) — location scope overrides

Type 2 (assumption override) also includes location scope overrides. If the owner says "rerun this for the Spring Hill location instead" or "what if this happened at both locations", treat it as a Type 2 update that changes the location scope. The marker format is:

> "[Updated] Scope revised from [old scope] to [new scope] — results below"

Example:

> "[Updated] Scope revised from Dauphin Street only to all active locations — results below"

---

## 8. Anti-Patterns / Never Do

From Scenario Lab v1.3 "What You Never Do" list (multi-location additions):

- **Never aggregate location-specific impact into business-wide projections without flagging.** If a scenario affects one location, the math stays scoped to that location.
- **Never assume single-location operation when `locations[].length > 1`.** Always determine scope before running the math.
- **Never reference `hq_location` as a standalone field.** Always read from `locations[]` and use the `headquarters` or `flagship` role (or first active location as fallback).

From Classifier V4.1 ANTI-HALLUCINATION RULES (multi-location additions):

- **Never assume single-location operation when the `locations[]` array indicates multiple active locations.** Always read `locations[]` before classifying `operational_model` and `geographic_context`.
- **Never collapse multi-location geographic context into a single primary location's description when the locations materially differ.** Each distinct market deserves its own `geographic_context` capture.
