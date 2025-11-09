# 🧠 SalesTalk Ontology v0

**Version:** 0.1  
**Author:** Data Science Copilot  
**Date:** November 2025  
**Status:** Draft - Phase 3 Baseline

---

## 🎯 Purpose

This document defines the semantic layer for SalesTalk's conversational analytics engine. It establishes the core ontology that translates natural language business questions into structured understanding:

**Intent → Subject → Measure → Dimension → Time**

This structured representation enables:
- Accurate classification of user questions
- Precise data retrieval from tenant databases
- Trustworthy narrative generation with provenance
- Consistent evaluation and quality measurement

---

## 📐 Ontology Structure

Every user question is classified into a canonical form:

```json
{
  "intent": "what|why|compare|forecast|...",
  "subject": "revenue|margin|customers|...",
  "measure": "revenue|gm|aov|...",
  "dimension": {"region": "EMEA", "product?": "..."},
  "time": {"period": "Q3", "year": 2025, "window?": "last_90d"},
  "confidence": {"overall": 0.0-1.0, "components": {...}}
}
```

---

## 🎭 Intent Taxonomy

**Definition:** The analytical question type the user is asking.

### Primary Intents

| Intent | Description | Example Question | Expected Answer Type |
|--------|-------------|------------------|---------------------|
| **what** | Request for current state or specific value | "What is Q3 revenue?" | Single metric value |
| **why** | Explanation of cause or change | "Why did sales drop last month?" | Causal narrative |
| **compare** | Comparison between entities or periods | "Compare EMEA vs APAC revenue" | Comparative analysis |
| **trend** | Pattern or direction over time | "How is margin trending?" | Time series insight |
| **forecast** | Prediction of future values | "What's the expected Q4 revenue?" | Projection with confidence |
| **rank** | Ordered list by performance | "Top 5 products by revenue" | Ranked list |
| **drill** | Breakdown or decomposition | "Break down revenue by region" | Hierarchical detail |
| **anomaly** | Detection of unusual patterns | "Any unexpected changes?" | Outlier identification |
| **target** | Performance vs goal | "Are we on track for Q4 target?" | Gap analysis |
| **correlation** | Relationship between metrics | "Does pricing affect conversion?" | Association insight |

### Intent Hierarchy

```
what
├── what-value (single metric)
├── what-distribution (spread across dimension)
└── what-composition (part-to-whole)

why
├── why-change (variance explanation)
├── why-variance (gap to target)
└── why-pattern (underlying cause)

compare
├── compare-entities (regions, products, etc.)
├── compare-periods (time-over-time)
└── compare-cohorts (customer segments)

trend
├── trend-direction (up/down/flat)
├── trend-velocity (rate of change)
└── trend-seasonality (periodic pattern)
```

---

## 🏢 Subject Taxonomy

**Definition:** The business entity or domain the question is about.

### Core Subjects

| Subject | Description | Related Measures | Common Dimensions |
|---------|-------------|------------------|-------------------|
| **revenue** | Total sales value | revenue, arr, mrr | region, product, channel |
| **margin** | Profitability | gm, gm_pct, cm, ebitda | product, customer, region |
| **customers** | Customer base | customer_count, ltv, churn | segment, cohort, industry |
| **products** | Product portfolio | units_sold, sku_count, aov | category, brand, channel |
| **sales** | Sales process | pipeline, win_rate, cycle_time | rep, stage, source |
| **orders** | Transactions | order_count, order_value, frequency | channel, method, status |
| **operations** | Operational metrics | fulfillment_time, inventory_turns | warehouse, supplier |
| **marketing** | Marketing performance | cac, roas, leads | campaign, channel, geo |
| **finance** | Financial health | cash, runway, burn_rate | department, cost_center |
| **people** | Human resources | headcount, attrition, productivity | department, level, location |

### Subject Synonyms & Aliases

```json
{
  "revenue": ["sales", "bookings", "income", "top line"],
  "margin": ["profit", "gm", "gross margin", "contribution margin"],
  "customers": ["clients", "accounts", "users", "subscribers"],
  "products": ["items", "skus", "inventory", "catalog"],
  "orders": ["transactions", "purchases", "deals", "contracts"]
}
```

---

## 📊 Measure Taxonomy

**Definition:** The specific metric or KPI to compute.

### Financial Measures

| Measure | Formula/Definition | Unit | Typical Range |
|---------|-------------------|------|---------------|
| **revenue** | Sum of all sales | currency | 0 to ∞ |
| **arr** | Annual Recurring Revenue | currency | 0 to ∞ |
| **mrr** | Monthly Recurring Revenue | currency | 0 to ∞ |
| **gm** | Revenue - COGS | currency | -∞ to ∞ |
| **gm_pct** | (Revenue - COGS) / Revenue × 100 | percent | -∞ to 100 |
| **cm** | Revenue - Variable Costs | currency | -∞ to ∞ |
| **ebitda** | Earnings Before Interest, Tax, Depreciation, Amortization | currency | -∞ to ∞ |
| **net_income** | Revenue - All Expenses | currency | -∞ to ∞ |

### Customer Measures

| Measure | Formula/Definition | Unit | Typical Range |
|---------|-------------------|------|---------------|
| **customer_count** | Unique active customers | count | 0 to ∞ |
| **new_customers** | First-time customers in period | count | 0 to ∞ |
| **churn_count** | Lost customers in period | count | 0 to ∞ |
| **churn_rate** | (Churned / Starting) × 100 | percent | 0 to 100 |
| **retention_rate** | (Retained / Starting) × 100 | percent | 0 to 100 |
| **ltv** | Lifetime Value per customer | currency | 0 to ∞ |
| **cac** | Customer Acquisition Cost | currency | 0 to ∞ |
| **ltv_cac_ratio** | LTV / CAC | ratio | 0 to ∞ |

### Sales & Product Measures

| Measure | Formula/Definition | Unit | Typical Range |
|---------|-------------------|------|---------------|
| **units_sold** | Quantity of items sold | count | 0 to ∞ |
| **aov** | Average Order Value = Revenue / Orders | currency | 0 to ∞ |
| **asp** | Average Selling Price = Revenue / Units | currency | 0 to ∞ |
| **order_count** | Number of transactions | count | 0 to ∞ |
| **win_rate** | (Wins / Opportunities) × 100 | percent | 0 to 100 |
| **pipeline_value** | Sum of open opportunities | currency | 0 to ∞ |
| **cycle_time** | Avg days from lead to close | days | 0 to ∞ |

### Operational Measures

| Measure | Formula/Definition | Unit | Typical Range |
|---------|-------------------|------|---------------|
| **fulfillment_time** | Days from order to delivery | days | 0 to ∞ |
| **inventory_turns** | COGS / Avg Inventory | ratio | 0 to ∞ |
| **stockout_rate** | (Stockouts / Total SKUs) × 100 | percent | 0 to 100 |
| **productivity** | Output per employee | varies | 0 to ∞ |
| **utilization** | (Used / Capacity) × 100 | percent | 0 to 100 |

---

## 🎯 Dimension Taxonomy

**Definition:** Attributes that slice/filter/group the data.

### Spatial Dimensions

| Dimension | Values | Hierarchy | Example |
|-----------|--------|-----------|---------|
| **region** | EMEA, AMER, APAC, LATAM, MEA | region → country → city | "EMEA" |
| **country** | ISO country codes | region → country → city | "US", "UK", "DE" |
| **city** | City names | region → country → city | "London", "New York" |
| **territory** | Sales territories | region → territory → rep | "West Coast" |

### Product Dimensions

| Dimension | Values | Hierarchy | Example |
|-----------|--------|-----------|---------|
| **product** | Product names/IDs | category → product → sku | "Enterprise Plan" |
| **category** | Product categories | category → product | "SaaS", "Hardware" |
| **brand** | Brand names | brand → product | "Premium", "Basic" |
| **sku** | Stock Keeping Units | product → sku | "ENT-001" |

### Customer Dimensions

| Dimension | Values | Hierarchy | Example |
|-----------|--------|-----------|---------|
| **segment** | SMB, Mid-market, Enterprise | segment → customer | "Enterprise" |
| **industry** | Industry verticals | industry → customer | "Healthcare", "Finance" |
| **cohort** | Time-based grouping | cohort → customer | "2024-Q1", "Jan-2025" |
| **account_tier** | Platinum, Gold, Silver, Bronze | tier → customer | "Gold" |

### Channel Dimensions

| Dimension | Values | Hierarchy | Example |
|-----------|--------|-----------|---------|
| **channel** | Direct, Partner, Online, Retail | channel → method | "Partner" |
| **source** | Lead/order source | source → campaign | "Organic", "Paid Search" |
| **campaign** | Marketing campaigns | source → campaign | "Q4-Promo" |
| **method** | Payment/delivery method | channel → method | "Credit Card", "Invoice" |

### People Dimensions

| Dimension | Values | Hierarchy | Example |
|-----------|--------|-----------|---------|
| **rep** | Sales representative | team → rep | "John Smith" |
| **team** | Organizational teams | division → team → rep | "Sales-West" |
| **department** | Business departments | department → team | "Sales", "Marketing" |
| **level** | Employee level | level → employee | "IC", "Manager", "Director" |

---

## ⏰ Time Taxonomy

**Definition:** Temporal scope and granularity for the analysis.

### Time Structure

```json
{
  "period": "Q3|2024-09|last_month|ytd|...",
  "year": 2025,
  "quarter": 3,
  "month": 9,
  "window": "last_90d|l12m|mtd|qtd|ytd",
  "comparison": "yoy|qoq|mom|wow|prev_period",
  "granularity": "day|week|month|quarter|year"
}
```

### Absolute Periods

| Period Type | Format | Examples | Interpretation |
|-------------|--------|----------|----------------|
| **Year** | YYYY | "2025", "2024" | Calendar year |
| **Quarter** | YYYY-Qn or Qn | "2025-Q3", "Q3" | Calendar quarter (current year if not specified) |
| **Month** | YYYY-MM or Month name | "2024-09", "September" | Calendar month |
| **Week** | YYYY-Wnn | "2025-W23" | ISO week |
| **Date** | YYYY-MM-DD | "2025-09-15" | Specific day |

### Relative Periods

| Period | Meaning | Calculation |
|--------|---------|-------------|
| **today** | Current day | date = current_date |
| **yesterday** | Previous day | date = current_date - 1 day |
| **this_week** | Current week | week = current_week |
| **last_week** | Previous week | week = current_week - 1 |
| **this_month** | Current month | month = current_month |
| **last_month** | Previous month | month = current_month - 1 |
| **this_quarter** | Current quarter | quarter = current_quarter |
| **last_quarter** | Previous quarter | quarter = current_quarter - 1 |
| **this_year** | Current year | year = current_year |
| **last_year** | Previous year | year = current_year - 1 |

### Rolling Windows

| Window | Meaning | Calculation |
|--------|---------|-------------|
| **last_7d** | Last 7 days | date >= current_date - 7 days |
| **last_30d** | Last 30 days | date >= current_date - 30 days |
| **last_90d** | Last 90 days | date >= current_date - 90 days |
| **l12m** | Last 12 months | month >= current_month - 12 |
| **l4q** | Last 4 quarters | quarter >= current_quarter - 4 |

### Period-to-Date

| Period | Meaning | Calculation |
|--------|---------|-------------|
| **mtd** | Month-to-date | Start of current month to today |
| **qtd** | Quarter-to-date | Start of current quarter to today |
| **ytd** | Year-to-date | Start of current year to today |
| **wtd** | Week-to-date | Start of current week to today |

### Comparison Types

| Comparison | Description | Formula |
|------------|-------------|---------|
| **yoy** | Year-over-year | current_year vs (current_year - 1), same period |
| **qoq** | Quarter-over-quarter | current_quarter vs (current_quarter - 1) |
| **mom** | Month-over-month | current_month vs (current_month - 1) |
| **wow** | Week-over-week | current_week vs (current_week - 1) |
| **vs_target** | Actual vs target/goal | actual vs planned/budgeted |
| **vs_prev_period** | Current vs immediately previous | depends on period type |

---

## 🎨 Classification Output Format

Every classified question must conform to this schema:

```json
{
  "intent": {
    "primary": "compare",
    "secondary": "trend",
    "confidence": 0.92
  },
  "subject": {
    "primary": "revenue",
    "related": ["sales", "bookings"],
    "confidence": 0.95
  },
  "measure": {
    "primary": "revenue",
    "aggregation": "sum",
    "unit": "USD",
    "confidence": 0.88
  },
  "dimension": {
    "region": {
      "value": "EMEA",
      "confidence": 0.90
    },
    "product": {
      "value": null,
      "confidence": 0.0
    }
  },
  "time": {
    "period": "2024-Q3",
    "comparison": "yoy",
    "granularity": "quarter",
    "confidence": 0.85
  },
  "confidence": {
    "overall": 0.87,
    "components": {
      "intent": 0.92,
      "subject": 0.95,
      "measure": 0.88,
      "dimension": 0.90,
      "time": 0.85
    }
  },
  "metadata": {
    "original_query": "How does EMEA revenue in Q3 compare to last year?",
    "normalized_query": "compare revenue for region=EMEA in 2024-Q3 vs 2023-Q3",
    "classifier_version": "v0.1",
    "timestamp": "2025-11-09T12:34:56Z"
  }
}
```

---

## 📏 Quality Standards

### Confidence Thresholds

| Component | High Confidence | Medium Confidence | Low Confidence | Action |
|-----------|----------------|-------------------|----------------|--------|
| **Overall** | ≥ 0.80 | 0.60 - 0.79 | < 0.60 | Refuse if < 0.60 |
| **Intent** | ≥ 0.85 | 0.70 - 0.84 | < 0.70 | Request clarification |
| **Subject** | ≥ 0.85 | 0.70 - 0.84 | < 0.70 | Request clarification |
| **Measure** | ≥ 0.80 | 0.65 - 0.79 | < 0.65 | Request clarification |
| **Dimension** | ≥ 0.75 | 0.60 - 0.74 | < 0.60 | Assume default or none |
| **Time** | ≥ 0.75 | 0.60 - 0.74 | < 0.60 | Assume most recent |

### Refusal Policy

The system **must refuse** to answer when:

1. **Overall confidence < 0.60** → "I'm not confident I understood your question. Could you rephrase?"
2. **Intent unclear** → "Are you asking for a comparison, a trend, or a specific value?"
3. **Subject ambiguous** → "Do you mean revenue, margin, or another metric?"
4. **Hallucination risk detected** → "I don't have sufficient data to answer this accurately."
5. **Out-of-scope question** → "This question is outside my current capabilities."

**Never guess or hallucinate. Prefer refusal over incorrect answers.**

---

## 🔄 Evolution & Versioning

### Current Version: v0.1

**Coverage:**
- ✅ Core financial measures (revenue, margin, etc.)
- ✅ Customer metrics (count, churn, ltv)
- ✅ Sales & product metrics
- ✅ Common dimensions (region, product, time)
- ✅ Standard time periods and comparisons

**Known Gaps:**
- 🚧 Marketing attribution metrics (partial)
- 🚧 Advanced operational metrics (inventory, supply chain)
- 🚧 HR/people analytics (partial)
- 🚧 Custom tenant-specific dimensions

### Planned Expansions (v0.2+)

1. **Intent refinement:**
   - Add `explain` (educational content)
   - Add `suggest` (recommendation)
   - Add `alert` (proactive notification setup)

2. **Subject coverage:**
   - Add `supply_chain` (logistics, inventory)
   - Add `marketing_attribution` (touchpoints, conversion)
   - Add `customer_health` (NPS, engagement scores)

3. **Dimension flexibility:**
   - Support tenant-specific custom dimensions
   - Add hierarchical drill-down (e.g., region → country → city)
   - Add multi-value filters (e.g., "regions EMEA and APAC")

4. **Time complexity:**
   - Add forecast horizons (e.g., "next 6 months")
   - Add multi-period aggregations (e.g., "trailing 12 months avg")
   - Add seasonality adjustment

### Versioning Policy

- **Major version (0.x → 1.x):** Breaking changes to schema or semantics
- **Minor version (0.1 → 0.2):** Backward-compatible additions (new intents, subjects, measures)
- **Patch version (0.1.0 → 0.1.1):** Bug fixes, clarifications, examples

All classifiers must output `classifier_version` in metadata for auditability.

---

## 🧪 Example Classifications

### Example 1: Simple What Query

**User Question:** "What is our Q3 revenue?"

**Classification:**
```json
{
  "intent": {"primary": "what", "confidence": 0.95},
  "subject": {"primary": "revenue", "confidence": 0.98},
  "measure": {"primary": "revenue", "aggregation": "sum", "confidence": 0.98},
  "dimension": {},
  "time": {"period": "2025-Q3", "granularity": "quarter", "confidence": 0.90},
  "confidence": {"overall": 0.94}
}
```

### Example 2: Comparative Analysis

**User Question:** "Compare EMEA vs APAC revenue for last quarter"

**Classification:**
```json
{
  "intent": {"primary": "compare", "confidence": 0.92},
  "subject": {"primary": "revenue", "confidence": 0.95},
  "measure": {"primary": "revenue", "aggregation": "sum", "confidence": 0.95},
  "dimension": {
    "region": {"value": ["EMEA", "APAC"], "confidence": 0.90}
  },
  "time": {"period": "last_quarter", "granularity": "quarter", "confidence": 0.85},
  "confidence": {"overall": 0.91}
}
```

### Example 3: Trend Query

**User Question:** "How is gross margin trending this year?"

**Classification:**
```json
{
  "intent": {"primary": "trend", "confidence": 0.88},
  "subject": {"primary": "margin", "confidence": 0.92},
  "measure": {"primary": "gm_pct", "aggregation": "avg", "confidence": 0.85},
  "dimension": {},
  "time": {"period": "ytd", "granularity": "month", "confidence": 0.82},
  "confidence": {"overall": 0.86}
}
```

### Example 4: Why Query (Causal)

**User Question:** "Why did customer churn increase last month?"

**Classification:**
```json
{
  "intent": {"primary": "why", "secondary": "compare", "confidence": 0.80},
  "subject": {"primary": "customers", "confidence": 0.90},
  "measure": {"primary": "churn_rate", "aggregation": "rate", "confidence": 0.88},
  "dimension": {},
  "time": {
    "period": "last_month",
    "comparison": "mom",
    "granularity": "month",
    "confidence": 0.85
  },
  "confidence": {"overall": 0.85}
}
```

### Example 5: Multi-Dimensional Drill

**User Question:** "Break down revenue by region and product category for Q2"

**Classification:**
```json
{
  "intent": {"primary": "drill", "confidence": 0.90},
  "subject": {"primary": "revenue", "confidence": 0.95},
  "measure": {"primary": "revenue", "aggregation": "sum", "confidence": 0.95},
  "dimension": {
    "region": {"value": "all", "confidence": 0.88},
    "category": {"value": "all", "confidence": 0.88}
  },
  "time": {"period": "2025-Q2", "granularity": "quarter", "confidence": 0.92},
  "confidence": {"overall": 0.92}
}
```

---

## 🔗 Integration Points

### For Classifiers

1. **Input:** Raw user question string
2. **Output:** JSON conforming to classification schema
3. **Context:** Tenant ID, user history, available data sources
4. **Constraints:** Response time < 500ms, confidence calibration required

### For Data Retrieval

1. **Input:** Classification JSON
2. **Output:** Query results with provenance
3. **Validation:** Check measure availability, dimension values, time range
4. **Fallback:** Return partial results if some dimensions unavailable

### For Narrative Generation

1. **Input:** Classification + data results
2. **Output:** Natural language response with references
3. **Requirements:** All numeric claims must cite source data
4. **Safety:** Include confidence caveats for low-confidence classifications

### For Evaluation

1. **Gold dataset:** Questions with ground-truth labels
2. **Metrics:** Per-component accuracy, calibration, overall F1
3. **Threshold:** Overall accuracy ≥ 80% for production deployment
4. **Monitoring:** Daily evaluation on rotating samples

---

## 📚 References

- **MVP_spec.md:** Product requirements and user personas
- **KPI_BASELINE.md:** Accuracy targets and success criteria
- **Architecture.md:** System design and data model
- **evaluation/gold.json:** Labeled questions for testing
- **evaluation/adversarial.json:** Edge cases and ambiguous queries

---

## ✅ Review & Approval

- [ ] Data Science Lead: ___________________ Date: ___________
- [ ] Product Owner: ___________________ Date: ___________
- [ ] Architect: ___________________ Date: ___________

---

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-11-09 | Data Science Copilot | Initial draft with core taxonomy |

---

*This ontology will evolve based on real user questions and evaluation feedback. Expect regular updates as we learn from production usage.*
