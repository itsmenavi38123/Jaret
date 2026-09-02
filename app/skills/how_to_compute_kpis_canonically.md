---
name: how_to_compute_kpis_canonically
description: Canonical computation methods for every KPI LightSignal surfaces — cash runway, current ratio, quick ratio, AR Days, AP Days, DSO, gross margin, net margin, OpEx ratio, burn rate, debt-to-equity, interest coverage, DSCR, inventory turnover, CCC, customer concentration, revenue per employee, MRR growth, utilization rate, same-store sales growth, AOV, repeat customer rate, and any other industry-specific or business-specific KPIs added over time (RevPAR for hotels, prime cost for restaurants, gross profit per project for construction, etc.). The catalog is expandable — when LightSignal needs to surface a new KPI, it gets added here. Use whenever any agent or endpoint needs to compute a KPI value — the Financial Analyst calculating drawer numbers, the Business Health scoring engine computing category inputs, the Demand Forecasting agent needing financial context, or any tab that surfaces a number that must match across the product. This is the canonical source — agents and endpoints MUST NOT have their own divergent computation logic for these KPIs.
---

# How to Compute KPIs Canonically

## 1. Overview

This skill is what **AI agents follow at runtime** when they need to compute a KPI. The agent reads the skill, identifies the KPI's formula (from the catalog if present, or derives it by reasoning from the classifier output and business-type-appropriate accounting practices if not), pulls the relevant data from the payload, and computes the value.

**The backend does NOT hardcode KPI formulas.** Naveen's job is data plumbing: pull raw data from connectors (QuickBooks, POS systems, payment processors, and any other data sources LightSignal supports), package it into the payload, hand it to the agent. The agent follows this skill to do the actual computation.

This matters because:
- New KPIs don't require backend code changes — the agent derives them
- Granular per-business variations are handled naturally (agent reads classifier + skill, picks the right variant)
- Endpoint consolidation is solved at the skill level (same skill, same answer, regardless of which agent calls it)
- The catalog grows organically as classifier surfaces new business needs (see §4 catalog growth flow)

**Math reliability:** AI agents should use precise computation tools (calculator, code execution) for arithmetic, not rely on inference alone. Return the computed value AND the formula used (so derivations are traceable and reviewable).

---

## 2. Inputs

The skill receives:

- **Financial / operational data** — current period values from connector data: accounting systems (QuickBooks and others), POS systems (Toast, Square, Clover, Shopify POS, Lightspeed, etc.), payment processors (Stripe, Square Payments, etc.), e-commerce platforms, and any other connector LightSignal has access to. Some KPIs require values from multiple sources (e.g., AOV needs POS order data, not accounting data).
- **Prior period data** — same structure, prior period(s), for delta and trend computation
- **Full classifier output** — used for granular per-business-type calibration and KPI applicability (e.g., MRR Growth applies to subscription businesses, prime cost applies to restaurants, RevPAR applies to hotels)
- **Business profile** — for context (employee count, location count, seasonality, etc.)

The agent uses whatever data sources are available. When required data isn't connected (e.g., POS data missing for AOV computation), surface a `missing_data_notice` directing the owner to connect the relevant source.

---

## 3. Output Schema

Every KPI computation returns:

```json
{
  "kpi_id": "cash_runway",
  "value": 7.2,
  "unit": "months",
  "computation_method": "current cash balance / monthly burn rate",
  "computation_source": "catalogued",
  "inputs_used": {
    "current_cash_balance": 86400,
    "monthly_burn_rate": 12000
  },
  "data_sources": ["quickbooks"],
  "data_coverage_pct": 97,
  "missing_data_notice": null,
  "prior_period_value": 8.5,
  "delta": -1.3,
  "delta_direction": "down"
}
```

Field rules:
- `value` — null only if computation impossible due to missing inputs (e.g., division by zero, required input not available)
- `computation_source` — `"catalogued"` when the formula is from §4 catalog, `"derived"` when the AI derived it for an uncatalogued KPI
- When `computation_source: "derived"`, also include `derivation_reasoning` (string explaining why this formula was chosen for this business type) — this is what reviewers read when approving the derivation for catalog inclusion
- `data_sources` — array of which connectors provided the inputs (e.g., `["quickbooks"]`, `["toast_pos", "quickbooks"]`, `["shopify", "stripe"]`)
- `data_coverage_pct` — raw percentage of required inputs that were present, fresh, and reliable. The UI / consuming agent decides how to display this. The skill just reports the number.
- `missing_data_notice` — populated when inputs are missing or stale, including notes on which connectors would need to be added; null when complete
- `prior_period_value`, `delta`, `delta_direction` — populated when prior period data is available; null otherwise
- `inputs_used` — plain English keys describing the inputs consumed; the AI maps to actual data fields at runtime

---

## 4. KPI Definitions (Catalog)

This section is the **catalog of known KPI formulas**. It is **expandable** — the entries below are formulas that have been validated and locked. The catalog grows whenever the AI agent derives a new formula for an uncatalogued KPI and that derivation gets reviewed and approved.

**Catalog growth flow:**

1. Classifier identifies a business that needs KPIs — including some that may not be in this catalog yet (e.g., a hotel needs RevPAR, a construction business needs gross profit per project, a niche industry surfaces something new)
2. AI agent receives the KPI need + raw data + full classifier output + business profile
3. **If the KPI is in this catalog** → agent uses the catalogued formula (with any business-type variants documented for that KPI)
4. **If the KPI is NOT in this catalog** → agent derives the formula by:
   - **Starting with the classifier output** — understand what kind of business this is first (revenue model, operational format, industry, audience type, business stage, etc.)
   - **Reasoning about what's appropriate for THIS business type** — different business types use fundamentally different accounting approaches. Restaurants use prime cost (food + labor as % of revenue) as the operational metric, not generic gross margin. SaaS uses MRR-based metrics with deferred revenue recognition. Construction uses percentage-of-completion accounting and tracks change orders. Hotels use RevPAR (revenue per available room) and occupancy rate. There is no single "standard formula" that applies across business types — what counts as labor cost, what counts as inventory, how revenue is recognized, what margin means, all vary by business type.
   - **Deriving the formula using business-type-appropriate practices** — not generic accounting defaults
   - **Considering available data sources** — what's actually connected and what fields they expose — to ensure the formula can be computed with the data on hand

   **The classifier output anchors the derivation; it's not a tweak applied after.** And the granularity goes all the way down — not just to industry, but to the specific operating model.

   A "restaurant" isn't one thing. An omakase sushi restaurant with a 12-seat counter, tasting-menu-only, reservation-required is fundamentally different from a fast-casual chain, which is different from a food truck, which is different from a high-volume diner. They're all "restaurants" in classifier_output's `operational_format`, but `price_position`, `service_pattern`, `audience_type`, `offering_specifics`, `competitive_position`, and `key_constraints` differ — and those differences should drive the formula.

   The agent thinks: *"this is a high-end omakase sushi restaurant — 12-seat counter, tasting menu only, reservation-required, premium positioning. Revenue is per-seat per-night with very high check averages. Labor is mostly specialized salaried chefs, not hourly. Food cost runs 35-40% (vs 30% generic restaurant baseline) due to premium fish. Inventory turns daily (fresh fish), not weekly. Prime cost matters, but reservation fill rate matters as much. Customer concentration is less about one big client and more about repeat customer rate and waitlist depth."*

   It does NOT think: *"this is a restaurant, use generic restaurant formulas"* — that level of granularity throws away most of what the classifier said. **Use everything the classifier output gives you.**

5. Agent computes the value AND returns: the formula used, the **reasoning behind the choice** (what about the classifier output drove which formula decision), the data sources consumed, and a confidence note
6. Derived formulas are flagged for review — V1: human review focused on **correctness** (catching math errors, validating that the chosen approach matches how that business type is actually run, confirming the right data sources were used). NOT on adding granularity — the AI did that upfront.
7. Approved derivations are added to this catalog with the per-business-type variations the AI proposed
8. Future requests for the same KPI + same business type use the catalogued version. Different business types may produce different catalogued formulas for the same-named KPI — that's expected (e.g., "labor cost" formula for a restaurant differs from "labor cost" for a SaaS).

This is how the catalog grows organically: the AI does the business-specific derivation upfront from the classifier anchor; humans review for correctness. Same-named KPIs across business types coexist in the catalog as distinct variants.

Different business types may surface KPIs not currently listed: hotels (RevPAR, ADR, occupancy rate), restaurants (prime cost, table turn time), construction (gross profit per project, change order ratio), e-commerce (CAC, LTV, return rate), and many others. None of these are limitations — they're catalog entries waiting to happen, either through AI derivation at runtime or through proactive cataloguing.

**The skill itself is the canonical place for ALL KPI definitions, current and future.** No agent should bake its own formula into its prompt. No backend code should hardcode a formula. The AI agent reads this skill, follows it, and the catalog grows.

**Note on input names below:** described in plain English ("current cash balance", "monthly burn rate"). These are conceptual references — the AI agent maps them to the actual financial data values in the payload at runtime. There's no separate field-name binding step; the agent reads what's available and applies the formula.

> **On the formulas:** standard accounting/finance definitions. The catalog is grounded in established practice. When the AI derives a new formula, it should also ground in established practice — if no standard formula exists, the derivation should be flagged with lower confidence for stricter review.

---

### 4.1 Cash Runway
**Formula:** `current cash balance / monthly burn rate`
**Unit:** months
**Required inputs:** current cash balance, average monthly burn rate (trailing 3-month if available, else trailing 1-month)
**Edge cases:**
- If monthly burn rate is zero or negative (business is cash-positive): return `value: null` with `missing_data_notice: "Business is cash-flow positive; runway not applicable"` — surface as positive in narrative instead
- If current cash is negative: still compute (negative runway means already in distress)

---

### 4.2 Current Ratio
**Formula:** `current_assets / current_liabilities`
**Unit:** ratio
**Required inputs:** current assets, current liabilities
**Edge cases:**
- If `current_liabilities = 0`: return `value: null`, `missing_data_notice: "No current liabilities reported"`

---

### 4.3 Quick Ratio
**Formula:** `(current_assets - inventory) / current_liabilities`
**Unit:** ratio
**Required inputs:** current assets, inventory, current liabilities
**Edge cases:** same as Current Ratio
**Business-type calibration:** for service businesses with negligible inventory, equals Current Ratio — surface only Current Ratio to avoid duplication.

---

### 4.4 Gross Margin %
**Formula:** `(revenue - cogs) / revenue * 100`
**Unit:** percent
**Required inputs:** revenue, COGS
**Edge cases:**
- If `revenue = 0`: return `value: null`
- If `cogs` is not reported (some service businesses): set `cogs = 0` and surface `data_confidence: "low"` with notice "COGS not tracked separately"

---

### 4.5 Net Margin %
**Formula:** `net_income / revenue * 100`
**Unit:** percent
**Required inputs:** net income, revenue
**Edge cases:** if `revenue = 0`: return `value: null`

---

### 4.6 AR Days (DSO — Days Sales Outstanding)
**Formula:** `(accounts_receivable / revenue) * days_in_period`
**Unit:** days
**Required inputs:** accounts receivable balance, period revenue, days in period (typically 30 for monthly, 90 for quarterly, 365 for annual)
**Edge cases:** if `revenue = 0`: return `value: null`

---

### 4.7 AP Days (DPO — Days Payable Outstanding)
**Formula:** `(accounts_payable / cogs) * days_in_period`
**Unit:** days
**Required inputs:** accounts payable balance, period COGS, days in period
**Edge cases:** if `cogs = 0`: use `(accounts_payable / total_expenses) * days_in_period` and flag with notice

---

### 4.8 Inventory Turnover
**Formula:** `cogs / average_inventory` (annualized)
**Unit:** turns per year
**Required inputs:** COGS, average inventory (start + end / 2)
**Edge cases:** if `average_inventory = 0` or business has no inventory: return `value: null`, mark KPI as not applicable for this business
**Business-type calibration:** applies to inventory-based businesses (retail, restaurants, manufacturing). For service / SaaS, surface as N/A — the FO tile selection should already exclude it via classifier-driven KPI map.

---

### 4.9 Cash Conversion Cycle (CCC)
**Formula:** `DIO + DSO - DPO`
**Where:** DIO = Days Inventory Outstanding = `(inventory / cogs) * days_in_period`
**Unit:** days
**Required inputs:** all from §4.6, §4.7, plus inventory and COGS

---

### 4.10 Debt-to-Equity (D/E)
**Formula:** `total_debt / total_equity`
**Unit:** ratio
**Required inputs:** total debt (short-term + long-term), total equity
**Edge cases:**
- If `total_equity <= 0`: return `value: null`, surface notice "Negative equity — D/E not meaningful, use absolute debt level"
- If `total_debt = 0`: value is 0 (no leverage)

---

### 4.11 Interest Coverage Ratio
**Formula:** `ebit / interest_expense`
**Unit:** ratio (times)
**Required inputs:** EBIT, interest expense
**Edge cases:** if `interest_expense = 0`: value is null, surface notice "No interest expense — coverage not applicable"

---

### 4.12 DSCR (Debt Service Coverage Ratio)
**Formula:** `net_operating_income / total_debt_service`
**Unit:** ratio
**Required inputs:** net operating income, total debt service (principal + interest in period)
**Edge cases:** if `total_debt_service = 0`: value is null

---

### 4.13 Burn Rate
**Formula:** `monthly_cash_outflow - monthly_cash_inflow` (when negative — i.e., burning cash)
**Unit:** dollars per month
**Required inputs:** monthly cash outflows, monthly cash inflows
**Edge cases:** if business is cash-positive (inflows > outflows): return `value: null`, flag KPI as not applicable

---

### 4.14 OpEx Ratio
**Formula:** `operating_expenses / revenue * 100`
**Unit:** percent
**Required inputs:** operating expenses, revenue

---

### 4.15 Revenue per Employee
**Formula:** `annualized_revenue / employee_count`
**Unit:** dollars
**Required inputs:** revenue, employee count from business profile
**Edge cases:** if `employee_count = 0` (owner-only): return `value: null`

---

### 4.16 Customer Concentration %
**Formula:** `top_customer_revenue / total_revenue * 100`
**Unit:** percent
**Required inputs:** top customer revenue (or top N), total revenue
**Variants:** report top-1, top-3, or top-5 depending on classifier business type. SaaS / B2B usually reports top-5 or top-10; service businesses report top-1 or top-3.

---

### 4.17 MRR Growth (SaaS-specific)
**Formula:** `(current_mrr - prior_mrr) / prior_mrr * 100`
**Unit:** percent
**Required inputs:** current MRR, prior period MRR
**Applies when:** classifier `revenue_model = "subscription"` or similar
**Edge cases:** if `prior_mrr = 0` (first month): return value is null

---

### 4.18 Utilization Rate (services-specific)
**Formula:** `billable_hours / available_hours * 100`
**Unit:** percent
**Required inputs:** billable hours, available hours
**Applies when:** classifier indicates time-billed service business
**Edge cases:** if `available_hours = 0`: return value is null

---

### 4.19 Same-Store Sales Growth (retail / multi-location)
**Formula:** `(current_period_same_store_revenue - prior_period_same_store_revenue) / prior_period_same_store_revenue * 100`
**Unit:** percent
**Required inputs:** revenue from locations that existed in both periods
**Applies when:** business has ≥2 locations
**Edge cases:** if business has <2 locations: not applicable

---

### 4.20 AOV (Average Order Value)
**Formula:** `total_revenue / order_count`
**Unit:** dollars per order
**Required inputs:** total revenue, order count

---

### 4.21 Repeat Customer Rate
**Formula:** `customers_with_2plus_orders / total_customers * 100`
**Unit:** percent
**Required inputs:** customer order frequency data
**Edge cases:** requires customer-level data; if only aggregate revenue available, return `value: null`

---

## 5. Business-Type Applicability

Not every KPI applies to every business. The FO tab uses a classifier-driven KPI map (`kpi_relevance_map.json`) to select which 8 KPIs to surface per business type. This skill computes any KPI requested; the *selection* of which KPIs to surface lives in the map.

When a requested KPI is genuinely not applicable to this business (e.g., Inventory Turnover for a pure SaaS business): return `value: null`, `data_confidence: "n/a"`, `missing_data_notice: "Not applicable for this business type"`. The tab UI should already filter these out before requesting — but defensive return prevents incorrect surfacing.

---

## 6. Period Definitions

- **Current period** — typically the most recent complete month (MTD if querying mid-month)
- **Prior period** — the period before current (typically prior month for MoM comparison; can be prior quarter or prior year on request)
- **Days in period** — 30 for monthly, 90 for quarterly, 365 for annual — used in days-based ratio calculations (DSO, DPO, DIO)

---

## 7. Data Coverage Reporting

Every computation returns a raw `data_coverage_pct` (0-100) representing how complete and fresh the inputs were:
- 100 = all required inputs present, fresh (≤7 days old), reliable
- Lower numbers reflect missing inputs (using fallback or estimate), stale data (>7 days, >30 days), or connector sync issues

The skill reports the raw percentage. Downstream consumers decide display:
- Drawer UI might show "Confidence: 97%" or a colored dot
- An agent might use the number to decide whether to caveat its narrative
- A different surface might bucket it for at-a-glance treatment

The skill does NOT prescribe display tiers. Report the number; let the consumer interpret.

**When data is genuinely not applicable** (e.g., Inventory Turnover for a pure SaaS): return `value: null`, `data_coverage_pct: null`, `missing_data_notice: "Not applicable for this business type"`. Distinct from "data missing" — this is "this metric doesn't exist for this business."

---

## 8. Universal Capability Skill Rule

This skill receives the FULL classifier output, which is the **anchor for how computation happens** — not a refinement applied after a generic formula. Use any relevant dimensions to determine what's appropriate for this business type:

- `operational_format` — affects what "revenue" and "cost" structures look like (transactional vs subscription vs project-based)
- `revenue_model` — drives revenue recognition approach (cash, accrual, percentage-of-completion, deferred)
- `audience_type` — affects metrics like Customer Concentration (top-1 for service businesses, top-10 for SaaS)
- `business_stage` — early vs mature affects what's a meaningful metric
- `geographic_context` — regional accounting nuances
- `service_pattern`, `supply_chain_distinctives`, `key_constraints`, `offering_specifics` — all may inform the formula choice

Plus `additional_dimensions`, `tags`, `multi_output`, `tensions`, `peer_pool`, `tier_b_signals_active`.

No artificial subset. If a dimension is in the classifier output and it informs how this business does accounting, the skill uses it. The classifier-driven derivation is what makes the same-named KPI mean different things for different businesses — and that's correct, not a bug.

For example, the Customer Concentration KPI looks different for a wedding catering business (top-3 by event matters), an enterprise SaaS (top-10 by annual contract value), and a high-end omakase restaurant (might not be meaningfully measured at all — repeat customer rate and waitlist depth matter more). All three are surfaced by classifier output if it's used in full. **Granularity goes as deep as the classifier output allows** — industry alone is not enough; combine industry, operating model, price position, audience, service pattern, business stage, and every other dimension that's relevant. Use them all.

---

## 9. Cross-References

- `how_to_calibrate_severity_status_from_peer_benchmarks` — once a KPI is computed, this skill assigns the 5-level status
- `LightSignal_FO_Tab_Spec_v1.md` §5 — KPI pool and tile selection
- `Financial_Analyst_Prompt_V5.txt` — FA's DRAWER MODE output consumes KPI values
- `lightsignal_current_state.md` §7.6 — peer benchmark architecture (downstream of this skill's outputs)
- `kpi_relevance_map.json` — classifier-driven KPI selection per business type

---

**End of skill.**
