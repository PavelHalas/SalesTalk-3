# 📊 SalesTalk KPI Baseline & Measurement Framework

**Version:** 1.0  
**Author:** Product Owner Copilot  
**Date:** November 2025  
**Status:** Phase 0 - Vision Inception

---

## 🎯 Purpose

This document defines the key performance indicators (KPIs) that will measure SalesTalk's success, establishes baseline targets for MVP, and outlines the measurement framework for continuous improvement.

**Core Principle:**  
*What gets measured gets improved. We measure what matters to users and the business.*

---

## 📈 KPI Framework Overview

SalesTalk success is measured across four dimensions:

1. **User Experience:** How quickly and easily users get value
2. **Accuracy & Trust:** How reliable and truthful the system is
3. **Engagement & Adoption:** How frequently users rely on the platform
4. **Business Impact:** How SalesTalk drives better decisions and outcomes

---

## 🎯 Primary KPIs (MVP Launch Targets)

### 1. Time to First Insight

**Definition:** Time elapsed from user login to receiving their first meaningful answer.

**Measurement:**
- **Start:** User authentication complete (JWT issued)
- **End:** First assistant message delivered with classification confidence ≥ 70%
- **Exclusions:** Initial onboarding tutorial, system errors

**Targets:**

| Metric | MVP Target | Stretch Goal | Measurement Frequency |
|--------|-----------|--------------|----------------------|
| **Median Time** | < 2 minutes | < 1 minute | Daily |
| **P95 Time** | < 5 minutes | < 3 minutes | Daily |
| **P99 Time** | < 10 minutes | < 7 minutes | Weekly |

**Success Criteria:**
- ✅ 80% of users get first insight in < 2 minutes
- ✅ No user waits more than 10 minutes (excluding system outages)

**Data Collection:**
```json
{
  "event": "first_insight_delivered",
  "tenantId": "tenant-123",
  "userId": "user-456",
  "sessionId": "session-789",
  "timeToInsightMs": 87340,
  "timestamp": "2025-11-09T12:34:56Z"
}
```

---

### 2. User Satisfaction (NPS)

**Definition:** Net Promoter Score measuring likelihood to recommend SalesTalk.

**Measurement:**
- **Survey Question:** "How likely are you to recommend SalesTalk to a colleague?" (0-10 scale)
- **Frequency:** After 5 successful conversations, then monthly
- **Calculation:** % Promoters (9-10) - % Detractors (0-6)

**Targets:**

| Period | MVP Target | Industry Benchmark | Notes |
|--------|-----------|-------------------|-------|
| **Month 1** | NPS ≥ 30 | SaaS avg: 30-40 | Early adopters, expect higher |
| **Month 3** | NPS ≥ 50 | Top quartile: 50+ | Product-market fit signal |
| **Month 6** | NPS ≥ 60 | Best-in-class: 60+ | Sustainable excellence |

**Success Criteria:**
- ✅ NPS ≥ 60 by Month 6
- ✅ Trend line positive across all cohorts
- ✅ < 10% detractors (scores 0-6)

**Segmentation:**
- By user persona (RevOps, Sales Leader, Finance)
- By company size (SMB, Mid-market, Enterprise)
- By use case frequency (Daily, Weekly, Occasional)

---

### 3. Conversation-to-Action Ratio

**Definition:** Percentage of conversations that lead to a shared insight, saved result, or follow-up action.

**Measurement:**
- **Numerator:** Conversations where user takes action (share, save, export, follow-up question)
- **Denominator:** Total completed conversations (≥ 2 message exchanges)

**Targets:**

| Metric | MVP Target | Post-MVP Goal | Rationale |
|--------|-----------|---------------|-----------|
| **Action Rate** | > 40% | > 60% | High engagement signals value |
| **Share Rate** | > 15% | > 25% | Collaboration indicator |
| **Follow-up Rate** | > 50% | > 70% | User explores deeper |

**Success Criteria:**
- ✅ 40% of conversations produce actionable output
- ✅ Shared insights have ≥ 2 viewers on average
- ✅ < 20% single-question abandonment rate

**Action Types Tracked:**
1. **Save Insight:** User bookmarks conversation
2. **Share with Team:** User sends insight to colleagues
3. **Export Data:** User downloads underlying data
4. **Follow-up Question:** User asks related question within 5 minutes
5. **Create Alert:** User sets up notification based on insight

---

### 4. Data Accuracy Confidence

**Definition:** System's measured accuracy in classification, data retrieval, and narrative generation.

**Measurement:**
Multi-component metric tracking accuracy across the pipeline:

#### 4.1 Classification Accuracy

**Targets:**

| Component | MVP Target | Stretch Goal | Measurement Method |
|-----------|-----------|--------------|-------------------|
| **Intent** | ≥ 90% | ≥ 95% | Gold set evaluation |
| **Subject** | ≥ 85% | ≥ 92% | Gold set evaluation |
| **Measure** | ≥ 85% | ≥ 92% | Gold set evaluation |
| **Time** | ≥ 80% | ≥ 90% | Gold set evaluation |
| **Overall** | ≥ 80% | ≥ 88% | All components correct |

**Evaluation:**
- **Gold Dataset:** 50+ labeled user questions
- **Adversarial Dataset:** 30+ ambiguous/edge cases
- **Frequency:** Daily automated evaluation + manual spot checks

#### 4.2 Data Retrieval Accuracy

**Targets:**

| Metric | MVP Target | Acceptable Range | Red Flag |
|--------|-----------|------------------|----------|
| **Query Correctness** | ≥ 95% | 90-95% | < 90% |
| **Data Freshness** | ≤ 15 min lag | 15-30 min | > 30 min |
| **Completeness** | 100% | 98-100% | < 98% |

**Validation:**
- Compare retrieved values against source of truth (DynamoDB → ground truth)
- Automated integration tests with known data fixtures
- User feedback on "Is this correct?" prompts

#### 4.3 Narrative Factuality

**Targets:**

| Metric | MVP Target | Long-term Goal | Measurement |
|--------|-----------|----------------|-------------|
| **Hallucination Rate** | < 5% | < 2% | Manual review + automated checks |
| **Reference Coverage** | ≥ 95% | ≥ 98% | % of claims with data backing |
| **Confidence Calibration** | ±10% | ±5% | Stated vs actual accuracy |

**Success Criteria:**
- ✅ < 5% of responses contain unsupported claims
- ✅ ≥ 95% of numeric facts match source data exactly
- ✅ System refuses to answer when confidence < 70% (rather than hallucinate)

**Measurement Process:**
1. **Automated:** Check all numeric claims against retrieved data
2. **Sampled Manual:** Review 20 random responses/week for qualitative accuracy
3. **User Feedback:** "Report inaccuracy" button tracking

---

## 📊 Secondary KPIs (Supporting Metrics)

### 5. Enterprise Retention

**Definition:** Percentage of paying customers retained after 12 months.

**Target:** > 90% annual retention (post-MVP)

**Leading Indicators (MVP):**
- Weekly Active Users (WAU) ≥ 60% of licensed seats
- Support ticket volume trending down
- Feature adoption rate ≥ 70% for core features

---

### 6. System Performance

**Definition:** Technical performance metrics ensuring acceptable user experience.

**Targets:**

| Metric | MVP Target | Red Line | Monitoring |
|--------|-----------|----------|------------|
| **Response Latency (P95)** | < 2 seconds | < 5 seconds | Real-time |
| **Availability (Uptime)** | > 99.5% | > 99.0% | Continuous |
| **Error Rate** | < 1% | < 3% | Real-time |
| **Token Cost per Query** | < $0.10 | < $0.25 | Daily |

**Success Criteria:**
- ✅ P95 response time under 2 seconds
- ✅ Less than 1% of queries result in system errors
- ✅ Average cost per conversation < $0.50

---

### 7. Data Quality & Freshness

**Definition:** Quality of data pipeline and tenant data health.

**Targets:**

| Metric | MVP Target | Acceptable | Remediation SLA |
|--------|-----------|------------|-----------------|
| **Data Freshness** | < 15 min lag | < 30 min | 1 hour |
| **Schema Validity** | 100% | ≥ 99% | Immediate |
| **Missing Values** | < 1% | < 5% | 24 hours |
| **Duplicate Records** | 0% | < 0.1% | Immediate |

---

### 8. Security & Compliance

**Definition:** Tenant isolation and data security metrics.

**Targets:**

| Metric | MVP Target | Tolerance | Response |
|--------|-----------|-----------|----------|
| **Cross-Tenant Data Leaks** | 0 | 0 | Immediate incident |
| **Failed Auth Attempts** | Track | < 5% | Alert at 10% |
| **Audit Log Coverage** | 100% | 100% | Required |
| **Encryption at Rest** | 100% | 100% | Required |

**Success Criteria:**
- ✅ Zero cross-tenant data access incidents
- ✅ 100% of sensitive operations logged
- ✅ All data encrypted (DynamoDB SSE, S3 SSE)

---

## 📐 Measurement Infrastructure

### Data Collection Strategy

#### 1. Application Telemetry
```json
// Example event structure
{
  "eventType": "conversation.completed",
  "tenantId": "tenant-abc123",
  "userId": "user-xyz789",
  "sessionId": "session-uuid",
  "timestamp": "2025-11-09T12:34:56Z",
  "metadata": {
    "messageCount": 5,
    "classificationConfidence": 0.87,
    "responseTimeMs": 1834,
    "actionTaken": "insight_shared",
    "modelUsed": "bedrock-claude-v1",
    "tokenCount": 1247
  }
}
```

#### 2. CloudWatch Custom Metrics
- `TimeToFirstInsight` (ms, per tenant)
- `ClassificationAccuracy` (%, daily evaluation)
- `ConversationActionRate` (%, hourly rollup)
- `HallucinationRate` (%, manual reviews)
- `ResponseLatencyP95` (ms, real-time)

#### 3. User Feedback Collection
- Post-conversation satisfaction (thumbs up/down)
- "Report inaccuracy" button
- Monthly NPS survey
- Quarterly user interviews

#### 4. A/B Testing Framework
- Compare classification models
- Test narrative templates
- Optimize conversation flows
- Measure feature impact

---

## 🎯 Success Thresholds & Gating

### MVP Launch Criteria (Must-Pass)

| KPI | Minimum Threshold | Status | Owner |
|-----|------------------|--------|-------|
| Time to First Insight (median) | < 3 minutes | 🔲 Pending | Product |
| Classification Accuracy (overall) | ≥ 75% | 🔲 Pending | Data Science |
| Hallucination Rate | < 8% | 🔲 Pending | Data Science |
| Response Latency (P95) | < 5 seconds | 🔲 Pending | Developer |
| Data Retrieval Accuracy | ≥ 90% | 🔲 Pending | Data Engineer |
| Zero Cross-Tenant Leaks | 100% isolation | 🔲 Pending | Architect |

**Gate:** All thresholds must be met before MVP launch to production.

---

### Post-Launch Monitoring

#### Week 1-2: Stabilization
- Focus: Performance, errors, critical bugs
- Review: Daily standups
- Escalation: Any red-line breach

#### Week 3-4: Early Adoption
- Focus: User satisfaction, time to insight
- Review: 2x per week
- Target: NPS ≥ 30, TTI median < 2 min

#### Month 2-3: Product-Market Fit
- Focus: Conversation-to-action ratio, retention signals
- Review: Weekly
- Target: Action rate > 40%, WAU > 60%

#### Month 4-6: Scale & Optimize
- Focus: Cost efficiency, accuracy improvements
- Review: Bi-weekly
- Target: NPS ≥ 60, hallucination < 3%

---

## 📊 Reporting Cadence

### Daily Dashboards (Automated)
- Response latency (P50, P95, P99)
- Error rate and top error types
- Active users and conversation count
- Token cost per tenant

### Weekly Reports (Product Owner)
- Time to first insight trends
- Classification accuracy on gold set
- Top user questions and pain points
- Feature adoption metrics

### Monthly Executive Summary
- NPS and user satisfaction trends
- Conversation-to-action ratio
- Business impact stories (case studies)
- Roadmap priorities based on data

### Quarterly Business Review
- Retention and expansion metrics
- ROI analysis (time saved, decisions improved)
- Competitive positioning
- Strategic roadmap alignment

---

## 🔄 Continuous Improvement Process

### Feedback Loop

```
User Interaction
    ↓
Telemetry Collection
    ↓
KPI Calculation
    ↓
Anomaly Detection
    ↓
Root Cause Analysis
    ↓
Prioritization (Product Owner)
    ↓
Experiment Design
    ↓
A/B Test
    ↓
Measure Impact
    ↓
Roll Out or Roll Back
    ↓
(repeat)
```

### Escalation Triggers

| Condition | Severity | Response Time | Owner |
|-----------|----------|---------------|-------|
| Cross-tenant leak | **Critical** | Immediate | Architect |
| Hallucination spike (>10%) | **High** | 4 hours | Data Science |
| Availability < 99% | **High** | 2 hours | Developer |
| NPS drop > 10 points | **Medium** | 24 hours | Product Owner |
| Classification accuracy < 70% | **Medium** | 48 hours | Data Science |
| TTI median > 5 min | **Low** | 1 week | Product Owner |

---

## 🎯 Success Definition (3-Month Checkpoint)

SalesTalk MVP is considered successful if:

✅ **User Experience:**  
- Time to first insight (median) < 2 minutes
- NPS ≥ 50

✅ **Accuracy & Trust:**  
- Classification accuracy ≥ 80%
- Hallucination rate < 5%
- Zero critical security incidents

✅ **Engagement:**  
- Conversation-to-action ratio > 40%
- 60% Weekly Active Users (of licensed seats)

✅ **Business Impact:**  
- 3+ documented case studies of better decisions
- 90-day retention ≥ 85%

**If targets are not met:**
1. Conduct user research to identify root causes
2. Prioritize top 3 improvements
3. Set 30-day improvement sprint
4. Re-evaluate with updated targets

---

## 📝 Appendix: Baseline Data Collection Plan

### Phase 0 (Pre-Launch)
- [ ] Set up CloudWatch custom metrics
- [ ] Implement event logging infrastructure
- [ ] Create automated gold set evaluation pipeline
- [ ] Build KPI dashboard (Grafana or CloudWatch)

### Phase 1 (Pilot - 10 Users)
- [ ] Collect baseline time-to-insight data
- [ ] Manual review of 100% of conversations
- [ ] Track classification accuracy on real queries
- [ ] Gather qualitative feedback (interviews)

### Phase 2 (Limited Release - 50 Users)
- [ ] Implement NPS survey flow
- [ ] A/B test narrative templates
- [ ] Measure conversation-to-action ratio
- [ ] Establish cost-per-query baseline

### Phase 3 (General Availability - 200+ Users)
- [ ] Full automated KPI tracking
- [ ] Weekly trend analysis
- [ ] Cohort analysis (by persona, company size)
- [ ] Competitive benchmarking

---

## 🔗 Related Documents

- **VISION_BRIEF.md:** Product vision and user personas
- **MVP_spec.md:** Technical scope and architecture
- **Architecture.md:** System design and components
- **ONTOLOGY.md:** (Phase 3) Classification schema
- **EVALUATION.md:** (Phase 3) Gold dataset and test harness

---

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-09 | Product Owner Copilot | Initial baseline definition |

---

**Review & Approval:**

- [ ] Product Owner: ___________________ Date: ___________
- [ ] Data Science Lead: ___________________ Date: ___________
- [ ] Engineering Lead: ___________________ Date: ___________
- [ ] Executive Sponsor: ___________________ Date: ___________

---

*This framework will evolve as we learn from real users. Expect quarterly updates based on data and feedback.*
