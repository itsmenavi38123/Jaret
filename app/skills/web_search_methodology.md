---
name: web_search_methodology
description: When to call web search (and scrape) tools, how to construct queries that carry location and business specifics, how to handle empty results vs. tool failures, citation patterns, and the mandate to never present training memory as current market fact. Consolidates web search guidance from Scenario Lab v1.3, Classifier V4.1, Orchestrator v3.5.4, Financial Analyst V5, and Research Scout V3.
---

# Web Search Methodology and Grounding

This skill consolidates the web search / firecrawl_scrape / getWeather usage rules shared across LightSignal agents. Tool names vary by agent (Scenario Lab and Classifier reference generic "web search"; Orchestrator uses `web_search` + `firecrawl_scrape` + `getWeather`; Scout uses `firecrawl_search` + `firecrawl_scrape` + `getWeather`). The principles below apply regardless of which tool name an agent uses. Where an agent has additional rules specific to its own toolset, those are noted.

---

## 1. The Mandate — When You Must Search

You MUST call a search tool inline when the output contains an external factual claim that isn't already verified in the payload. Specifically:

- Any claim about a specific market, a specific city, local costs, local regulations, local competitive dynamics, current loan rates, current industry benchmarks, or current permit requirements (Scenario Lab "MANDATORY WEB SEARCH RULE")
- Insurance premium ranges (workers comp, general liability, commercial auto, professional liability)
- Wage rates, sign-on bonuses, compensation benchmarks
- Contract clause typicals (escalators, renewal terms, termination fees, exclusivity periods)
- Regulatory thresholds or deadlines
- Market-rate benchmarks (advertising spend by category, marketing ROI typicals, CAC ranges by industry)
- General vendor pricing ranges
- Geographic context — demographic profile, foot traffic patterns, economic drivers, tourist vs. local mix
- Competitive landscape — local competitors within a reasonable radius, recent openings/closings, pricing patterns
- Market dynamics in the business's industry within their geographic market
- The business's own public presence (website, social media, public listings) when classifying or contextualizing
- Live forecast data for outdoor-impacted business operational decisions in next 7–14 days (getWeather)

**Never present training memory as current market fact.** If the answer isn't in the payload and the lookup would have produced verified data, you must search. Skipping the tool and going straight to a hedge is a failure pattern.

---

## 2. When NOT to Search

- Don't search for things already verified in the payload.
- Don't search for individual customer names or vendor names from payload data (privacy and irrelevance).
- Don't search for personal/private details about the owner.
- Don't search exhaustively when basic classification or recommendation is clear from the profile/connector data alone.
- Don't search for general business principles that don't need verification (a $500-an-hour advisor doesn't search for "what is gross margin").
- Don't call getWeather for indoor-only businesses with no weather sensitivity, or for time windows beyond 14 days (forecast unreliable).
- Don't call getWeather for grants, RFPs, certifications, co-ops, accelerators, platform windows, or export programs.

---

## 3. Query Construction — The Single Most Important Quality Lever

Generic searches return generic results. Effective queries combine specific identifiers — location, market segment, business specifics, named entities, year — pulled directly from the payload.

**Effective patterns:**

- Business name + city + neighborhood → finds the business's own public presence
- Business type + neighborhood + city + current year → finds local market conditions (e.g., "downtown Mobile AL food truck market 2026", "Williamsburg Brooklyn boutique fitness studios 2026")
- Specific cuisine/product/service + neighborhood + city → narrows competitive research (e.g., "omakase Williamsburg Brooklyn", "B2B SaaS sales consulting agencies SoMa San Francisco")
- Operation specifics + location + size + year + sub-detail (insurance/wage/contract example): "workers comp insurance Mobile Alabama 3-employee food truck NAICS 722330 2026 premium range"
- Specific named entity for surgical lookup: "Gulf Smoke BBQ Mobile Alabama Government Street menu pricing 2026"

**Always include neighborhood when known** (Geographic Granularity Rule). City-only queries ("Brooklyn" or "Mobile") return mixed results across very different sub-areas and produce worse classification and worse recommendations.

**Avoid:**

- "restaurant" without geography
- "business" alone
- Regional rollups when neighborhood/city is known ("Southeast US food trucks")

**Side-by-side examples** (Orchestrator):

| Wrong (generic) | Right (carries specifics) |
|-----------------|---------------------------|
| "workers comp food service premiums" | "workers comp insurance Mobile Alabama 3-employee food truck NAICS 722330 2026 premium range" |
| "HOA landscape contract escalator percentages" | "HOA landscape maintenance contract annual escalator clause Phoenix Arizona West Valley 2026 commercial $100k to $400k contracts" |
| "Restaurant Depot produce pricing" | "Restaurant Depot Mobile Alabama vine-ripe tomato bell pepper romaine lettuce wholesale case price 2026" |
| "competitor food trucks" | "Gulf Smoke BBQ food truck Mobile Alabama Government Street menu pricing 2026" |

---

## 4. Two-Stage Workflow for Hyper-Local Data (Orchestrator + Scout)

For data that lives on a specific page but isn't well-summarized in search snippets (specific competitor menus, HOA board meeting minutes, individual property listings, specific business pricing pages, RFP postings), use the two-stage workflow:

1. **Call search** to discover the right URL (e.g., search "Gulf Smoke BBQ Mobile AL menu" returns their Facebook page, website, or Yelp listing).
2. **Identify the most authoritative URL** from results. Prefer the business's own page, Facebook business page, or primary listing. Avoid aggregator wrappers when better options exist.
3. **Call scrape** on that URL to retrieve the specific data (menu items with prices, hours, current offerings, etc.).
4. **Use the surgical data** in the recommendation with the source URL cited.

For broad lookups (market wage ranges, insurance premium typicals, regulatory thresholds), search alone is usually sufficient. For surgical lookups, the two-stage workflow is what gets the actual numbers the owner needs.

For opportunity discovery (Scout, Mode 1): **always scrape every candidate that passes the gate.** Snippets alone are never sufficient for opportunity extraction. Every opportunity card requires a full page extraction.

---

## 5. Search Priority Order Within the Payload-First Hierarchy

Across all agents, the source priority for any number, threshold, or external factual claim:

1. **Owner input** — if the owner specified the number in their question, that wins. Always.
2. **Connector data** (accounting, POS) — if the number exists, use it. Per-location data via QBO Class/Location or POS location tagging takes precedence over aggregated data for location-specific scenarios.
3. **Business profile** — if the number exists in the profile, use it.
4. **Web search / firecrawl_scrape** — if the number is external (market, local, current rate, benchmark) and not in the payload, search before using any default.
5. **Hedged labeled estimate** — only when search returned nothing useful AND general knowledge is sufficient to anchor a working range. Frame as advisor delegation to a specialist in the owner's network (broker, distributor rep, property manager). See `anti_hallucination_rules.md` Section 6.
6. **Skip the threshold entirely** when even general knowledge is too thin to estimate responsibly. Acknowledge the gap and deliver only what you can ground.

---

## 6. Citations — Integrate Naturally, Name Specific Sources

When a search or scrape returns content you use in a recommendation, integrate the citation naturally in the narrative. The goal: the owner reads a verified specific claim with the source baked in, not a vague hedge.

**Good citations** (specific, named sources, anchored numbers):

- "Workers comp for 3-employee food service in coastal Alabama runs $138 to $215 a month based on current Travelers, Hartford, and Liberty Mutual quote data for NAICS 722330 with no claims history"
- "Phoenix metro commercial landscape crew wages currently post between $19 and $24 an hour on ZipRecruiter and Indeed for similar operations, with the $22 to $24 band common during summer hiring scarcity"
- "Restaurant Depot Mobile currently lists vine-ripe tomatoes at $24 per 25lb case versus Sysco's $32 per 25lb case for the same product, a 25 percent gap" (when scraped from a specific page)
- "Gulf Smoke BBQ's current menu (pulled today from their Facebook business page) lists pulled-pork plates at $11.99 versus your Loaded Bowl at $14.20, a $2.21 gap at your primary lunch lot"

**Bad citations** (vague, unverifiable, no specific source):

- "Workers comp typically runs around $200 a month for similar operations"
- "Phoenix landscape wages are generally competitive"
- "Restaurant Depot prices are usually lower than Sysco"
- "Annual escalators are common in landscape contracts"

The bad versions look like hedged estimates that hint at the agent's general knowledge. The good versions look like an advisor who just looked something up — or scraped a specific page — and tells the owner exactly what they found, with the sources.

Per-agent citation formats:

- **Scout** cites via `notes_evidence` arrays, `source_url`, and `sources` JSON arrays.
- **Orchestrator and FA** integrate citations naturally inside narrative recommendation fields.
- **Classifier** cites the source briefly in the `reasoning` field of relevant dimensions.

---

## 7. Empty Results vs. Tool Failure

Distinguish two cases:

**Empty results.** Search ran successfully but returned nothing useful. Lower confidence on affected dimensions, note in reasoning fields, optionally add to `sparse_data_flags` if a specific search type returned consistently empty (e.g., "no public web presence found"). Then fall back to the hedged-labeled-estimate-with-advisor-delegation pattern if applicable.

**Tool failure.** Technical error — the search service is unreachable, query times out, or you receive an error response. Retry the query at least once before giving up. If retry also fails, proceed with the rest of the work using whatever data IS available, and note in `sparse_data_flags` that intended research was not completed (e.g., "competitive landscape research not available — search service unreachable after retry"). Never fabricate to fill the gap left by failed search.

If search returns conflicting information, note the conflict in reasoning rather than picking one silently.

---

## 8. Tool-Use Caps — Spend Them Wisely

Each agent has a finite tool-use cap per run (Orchestrator typically 8 web_search calls per Cascade; Scout limits by run type).

Spend search budget on:

- (a) specific external dollar amounts, percentages, or thresholds that need to anchor a recommendation
- (b) verifying competitor or vendor activity that changes the recommendation's framing
- (c) regulatory specifics that affect a binding decision
- (d) any time fabricating from training would risk staleness or geographic mismatch

Don't spend search budget on:

- Things already in the payload
- General principles that don't need verification
- Open-ended exploration when a tighter query would do

For multi-location businesses, allocate budget per active location rather than concentrating on one (see `multi_location_handling.md` Section 4).

---

## 9. Specific Categories That MUST Trigger a Tool Call

Before writing any of these in narrative, the appropriate tool MUST be called first (Orchestrator-most explicit version):

| Claim type | Tool to use |
|------------|-------------|
| Insurance premium range (workers comp, general liability, commercial auto, professional liability) | search |
| Wage rate, sign-on bonus, compensation benchmark | search |
| Contract clause typical (escalators, renewal terms, termination fees, exclusivity periods) | search for general guidance |
| Regulatory threshold or deadline | search |
| Market-rate benchmark | search |
| General vendor pricing range | search |
| Specific vendor's own pricing page or product catalog | two-stage workflow |
| Specific competitor's menu, hours, pricing, current offerings | two-stage workflow |
| Specific HOA board minutes, agendas, RFP postings | two-stage workflow |
| Specific business's website content | two-stage workflow |
| Specific property listing details | two-stage workflow |
| Live forecast for outdoor-impacted operational decisions next 7–14 days | getWeather |
| Severe weather risk inside an action window the recommendation hinges on | getWeather |
| Seasonal preparation timing (hurricane, monsoon, freeze, heat) materially affecting timing | getWeather + payload `seasonal_risk_events` |

The hedged-labeled-estimate fallback only applies AFTER tool attempts returned nothing useful. Skipping the tools and going straight to hedge is a failure pattern.

---

## 10. No Internal-Architecture Leakage in Owner-Facing Narrative

The lookup architecture is invisible to the owner. Never narrate it in owner-facing fields.

**Forbidden phrases** (Orchestrator):

- "Research Scout is investigating..."
- "Research Scout is pulling..."
- "Research Scout is looking up..."
- "Premium ranges will be in your next refresh"
- "This is being researched..."
- "TBD on next refresh"
- "Exact figure to follow"
- "Once we have the data..."
- "Pending Research Scout findings"

These are FAILS in narrative fields. Either give the verified data from the tool now, or fall back to the hedged labeled estimate framed as advisor delegation. Never defer.

You CAN reference the lookup capability in narrative when it adds credibility — "per current Mobile-area workers comp quote data from Travelers, Hartford, and Liberty Mutual" — without exposing the internal architecture.

---

## 11. Multi-Location Web Search Pattern (Classifier V4.1)

For multi-location businesses, the search budget allocates research to each location's specific market rather than concentrating on one.

- Run geographic-context searches for each active location separately (city + neighborhood combination).
- Run competitive-landscape searches around each location's address separately.
- If two locations share a neighborhood or city block, you may research them together to save budget.
- If locations are in different cities or different markets, research each market independently.

(See `multi_location_handling.md` Section 4 for the full multi-location research rule.)

---

## 12. Reconciliation notes

- **Tool naming.** Each agent should use its own tool names; the skill above stays tool-agnostic where possible. The three primary patterns are: search-only (Classifier, Scenario Lab), search + scrape (Orchestrator, Scout), and add-getWeather (Orchestrator, Scout).
- **Mandate vs. permission.** Scenario Lab's "MANDATORY" wording for market/local data and Orchestrator's "MANDATE" wording for any output containing external factual claims are the same rule with different scopes. The reconciled rule: if the output contains an external factual claim not in the payload, you must search.
- **What counts as "external factual claim"?** Reconciled definition combining all five prompts: anything that varies by region, industry, size, or time, and that the owner could fact-check by Googling. Insurance ranges, wage rates, contract typicals, regulatory specifics, competitor activity, vendor pricing — yes. "Smaller accounts are less price-sensitive than anchor clients" — no (general principle).
- **Persistent monitoring vs. inline lookup** (Orchestrator only). The `research_requests` JSON output field is for persistent monitoring (standing watches the backend runs across cycles), not for one-shot lookups. One-shot lookups go through inline tool calls now. Other agents do not have an analogous mechanism — they call their tools inline only.
