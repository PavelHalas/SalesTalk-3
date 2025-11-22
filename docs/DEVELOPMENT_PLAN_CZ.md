# Czech Language Support Implementation Plan

Last Updated: 2025-11-21
Owner: Developer Agent
Status: Active (Top Priority)

## 1. Vision
Achieve Czech (cs) classification parity with English across all intent types, subjects, measures, dimensions, and time expressions while maintaining <100ms added latency overhead and single canonical JSON schema output.

## 2. Objectives
- **Accuracy Parity**: CZ metrics within ≤3% of EN across intent, subject, measure, dimension, time.
- **Single Schema**: All classifications return canonical English tokens regardless of input language.
- **Transparent Normalization**: Czech inputs normalized to English equivalents pre-classification; no language mixing in output.
- **Performance**: Language detection + normalization overhead <100ms; total classification latency target maintained.

## 3. Current Baseline (English Only)
From recent test runs (deepseek-r1:latest):
- Intent: ~91% (88/97 successful)
- Subject: ~95% (92/97)
- Measure: ~95% (92/97)
- Dimension: ~74% (28/38 when expected)
- Time: Variable (~0-50% depending on phrase complexity)
- Parse failures: 3/100 (JSON errors)

**Target End-State (Both EN & CZ)**
- Intent: ≥97%
- Subject: ≥98%
- Measure: ≥96%
- Dimension: ≥92%
- Time: ≥95%
- Parse failures: <1%
- CZ vs EN delta: <3% all components

## 4. Architecture Overview

```
Czech Question
    ↓
[Language Detection] ← Fast heuristic + fallback embedding
    ↓
[Normalization Layer] ← Map CZ → canonical EN tokens
    ↓
[Existing Classification Pipeline] ← Unchanged; uses normalized tokens
    ↓
Canonical JSON (English tokens)
```

**Key Principles**
- Detection happens first (before any processing)
- Normalization is deterministic mapping (no model call)
- Classification layer remains language-agnostic (receives English tokens)
- Output always in canonical English schema
- Metadata tracks original language for telemetry

## 5. Phase Breakdown

### Phase 5.1: Detection & Normalization (Week 1)
**Goal**: Reliably identify Czech vs English; map Czech vocabulary to canonical tokens.

**Tasks**
1. **Language Detection (LANG_DETECT)** [Todo 15]
   - **Primary**: Stopword-based detection (Czech people often omit diacritics when typing)
     - Czech stopwords without diacritics: je, jsou, byl, byla, bylo, byli, jsem, jsi, jsme, jste, v, na, z, do, od, k, po, o, s, a, ale, nebo, tento, tato, toto, ten, ta, to, minuly, minula, minule, jaky, jaka, jake, ktery, ktera, ktere, kolik, proc, jak, kde, kdy
     - Match threshold: ≥2 Czech stopwords OR ≥30% stopword density
   - **Secondary**: Character pattern hints (optional boost, not required)
     - If diacritics present (č, ď, ě, ň, ř, š, ť, ů, ž), boost Czech confidence
   - **Fallback**: Embedding similarity for ambiguous cases (short queries <5 words with no stopwords)
   - Return: `{"language": "cs"|"en", "confidence": float}`
   - Environment flag: `ENABLE_LANG_DETECT=true`

2. **Czech Normalization Mapping (CZ_NORM)** [Todo 16]
   - **MANDATORY**: Support both diacritic and diacritic-free variants for ALL Czech phrases
   - Preprocessing: Strip diacritics before lookup (háčky: č→c, ď→d, ě→e, ň→n, ř→r, š→s, ť→t, ů→u, ž→z; čárky: á→a, é→e, í→i, ó→o, ú→u, ý→y)
   - Build bidirectional map: Czech phrase (normalized) → English canonical token
   - Coverage areas (all with diacritic-free variants):
     - Subjects: trzby/tržby→revenue, zakaznici/zákazníci→customers, objednavky/objednávky→orders, prodeje→sales, marze/marže→margin, zisk→profit
     - Metrics: mira odlivu/míra odlivu→churn_rate, prumerna hodnota objednavky/průměrná hodnota objednávky→aov
     - Intents: co→what, proc/proč→why, porovnat→compare, predpoved/předpověď→forecast, zebricek/žebříček→rank
     - Time: dnes→today, vcera/včera→yesterday, tento tyden/týden→this_week, minuly mesic/minulý měsíc→last_month, letosni rok/letošní rok→this_year
     - Dimensions: aktivni/aktivní→active, neaktivni/neaktivní→inactive
   - Implementation: `backend/lambda/normalization/cz_mapping.json` + `strip_diacritics()` utility
   - Normalization function: strip_diacritics() → longest-match-first lookup

3. **Integration Point**
   - Add normalization step in `classify.lambda_handler` before calling `ai_adapter`
   - Store original question + normalized question in metadata
   - Pass normalized question to existing classification pipeline

**Acceptance Criteria**
- Detection accuracy >98% on mixed EN/CZ dataset (100 samples)
- Normalization coverage: ≥90% common Czech phrases map correctly
- Added latency: <50ms p95

### Phase 5.2: Taxonomy Localization (Week 1-2)
**Goal**: Extend taxonomy files with Czech translations; maintain single source of truth.

**Tasks**
4. **Czech Taxonomy Extensions (CZ_TAXONOMY)** [Todo 17]
   - **MANDATORY**: Include BOTH diacritic and diacritic-free variants in all aliases
   - Extend each subject JSON with `translations.cs.aliases` array
   - Example structure:
     ```json
     {
       "subject": "revenue",
       "aliases": ["topline", "sales"],
       "translations": {
         "cs": {
           "aliases": ["tržby", "trzby", "obrat", "výnosy", "vynosy"],
           "display_name": "Tržby"
         }
       },
       "metrics": [
         {
           "id": "mrr",
           "aliases": ["monthly_recurring_revenue"],
           "translations": {
             "cs": {
               "aliases": ["měsíční opakující se tržby", "mesicni opakujici se trzby", "MRR"],
               "display_name": "Měsíční opakující se tržby"
             }
           }
         }
       ]
     }
     ```
   - Files to extend:
     - `taxonomy/subjects/*.json` (all 12 subjects)
     - `taxonomy/shared/dimensions.json` (region, segment, channel, status, productLine)
     - `taxonomy/shared/time.json` (periods, windows, granularity)

5. **Czech Dimensional Synonyms (CZ_DIM_SYN)** [Todo 27]
   - **MANDATORY**: All variants include diacritic-free forms
   - Region: "Severní Amerika"/"Severni Amerika"→North America, "Evropa"→Europe, "Asie-Tichomoří"/"Asie-Tichomori"→APAC
   - Segment: "malé a střední podniky"/"male a stredni podniky"→SMB, "podnik"→Enterprise
   - Channel: "maloobchod"→retail, "velkoobchod"→wholesale
   - Product Line: "software"→Software, "hardware"→Hardware, "služby"/"sluzby"→Services
   - Status: "aktivní"/"aktivni"→active, "neaktivní"/"neaktivni"→inactive

6. **Czech Time Tokens Extension (CZ_TIME)** [Todo 28]
   - **MANDATORY**: All time expressions in both diacritic and diacritic-free forms
   - Periods: vcera/včera, dnes, zitra/zítra, tento tyden/týden, minuly tyden/minulý týden, tento mesic/měsíc, minuly mesic/minulý měsíc, tento kvartal/kvartál, minuly kvartal/minulý kvartál, letosni rok/letošní rok, minuly rok/minulý rok
   - Windows: od zacatku roku/od začátku roku (ytd), od zacatku kvartalu/od začátku kvartálu (qtd), poslednich 3 mesice/posledních 3 měsíce (l3m), poslednich 6 mesicu/posledních 6 měsíců (l6m), poslednich 12 mesicu/posledních 12 měsíců (l12m)
   - Granularity: den, tyden/týden, mesic/měsíc, kvartal/kvartál, rok
   - Multi-period patterns: "Q3 vs Q4", "tento mesic/měsíc oproti minulemu/minulému"

**Acceptance Criteria**
- All 12 subjects have Czech translations
- Shared dimensions fully localized
- Time token coverage: ≥95% common Czech time phrases
- Taxonomy validation passes with new fields

### Phase 5.3: Prompt Adaptation (Week 2)
**Goal**: Support Czech examples in prompt without bloating English-only runs.

**Tasks**
7. **Dual-Language Prompt Adaptation (DUAL_PROMPT)** [Todo 18]
   - Modularize prompt into sections:
     - Core schema (language-agnostic)
     - Intent/subject/measure rules (English base)
     - Optional: Czech example block (2-3 examples)
   - When `language=cs` detected, insert Czech examples:
     ```
     Czech Examples:
     Q: "Jaké jsou naše tržby v Q3?"
     → {"intent":"what","subject":"revenue","measure":"revenue","time":{"period":"Q3","granularity":"quarter"}}
     
     Q: "Proč klesla míra odlivu minulý měsíc?"
     → {"intent":"why","subject":"customers","measure":"churn_rate","time":{"period":"last_month","granularity":"month"}}
     ```
   - Keep output schema instructions in English (canonical tokens only)
   - Add negative example: WRONG to use Czech tokens in output JSON

8. **Prompt Modularization (PROMPT_MOD)** [Todo 14]
   - Split `classification_prompt.txt` into sections:
     - `prompt_base.txt` (schema + core rules)
     - `prompt_intent_cues.txt` (intent disambiguation)
     - `prompt_examples_en.txt` (English examples)
     - `prompt_examples_cs.txt` (Czech examples)
   - Assembly function: `build_prompt(language, detected_tokens)`
   - Only include Czech section when `language=cs`

**Acceptance Criteria**
- Prompt assembly <5ms overhead
- Czech examples improve CZ accuracy by ≥5pp vs no examples
- No regression in English accuracy when Czech block absent

### Phase 5.4: Testing & Validation (Week 2-3)
**Goal**: Comprehensive Czech test coverage; measure parity with English.

**Tasks**
9. **Czech Contract Test Suite (CZ_TESTS)** [Todo 19]
   - **MANDATORY**: Test suite must include 50/50 split of diacritic vs diacritic-free questions
   - Create `backend/tests/data/product_owner_questions_cz.csv`
   - Coverage (target 80-100 questions):
     - All intent types (what, why, compare, trend, forecast, rank, breakdown, target, correlation, anomaly)
     - All subjects (revenue, customers, orders, sales, marketing, margin, profit, products, regions, segments, reps, productLines, timePeriods)
     - Common measures per family
     - Dimension combinations (region, segment, channel, status, productLine)
     - Time expressions (periods, windows, multi-period comparisons)
     - Rank queries with limits
     - Correlation with related_metric
   - Format identical to English CSV:
     ```csv
     question,intent,subject,measure,dimension,time
     "Jaké jsou naše tržby v Q3?","what","revenue","revenue","{}","{""period"":""Q3"",""granularity"":""quarter""}"
     ```

10. **Czech Evaluation Harness (CZ_EVAL)** [Todo 20]
    - Extend `backend/tests/e2e/test_product_owner_questions.py` to support Czech dataset
    - Add separate test class: `TestProductOwnerQuestionSuiteCzech`
    - Compute metrics:
      - Per-component accuracy (intent, subject, measure, dimension, time)
      - CZ vs EN delta (absolute percentage point difference)
      - Confusion matrices (where Czech fails vs English)
    - Generate summary report:
      ```
      Language: Czech
      Intent:     95.0% (76/80)  [EN: 97.0%, Δ: -2.0pp]
      Subject:    97.5% (78/80)  [EN: 98.0%, Δ: -0.5pp]
      Measure:    96.2% (77/80)  [EN: 96.0%, Δ: +0.2pp]
      Dimension:  90.0% (27/30)  [EN: 92.0%, Δ: -2.0pp]
      Time:       93.3% (42/45)  [EN: 95.0%, Δ: -1.7pp]
      ```

**Acceptance Criteria**
- Czech test suite: ≥80 questions covering all intents/subjects
- Evaluation harness runs successfully for both EN and CZ
- Initial CZ accuracy: ≥85% all components (before tuning)

### Phase 5.5: Confidence & Quality (Week 3)
**Goal**: Calibrate confidence scores; handle edge cases gracefully.

**Tasks**
11. **Czech Confidence Calibration (CZ_CONF)** [Todo 21]
    - Penalize classifications containing raw Czech tokens in output (mapping failure signal)
    - Boost confidence when all tokens successfully normalized
    - Add language-specific component to confidence score:
      ```python
      language_penalty = 0.0
      if language == "cs":
          if contains_czech_diacritics(output_json):
              language_penalty = 0.2  # Failed to normalize
          if normalized_token_coverage < 0.9:
              language_penalty += 0.1  # Incomplete mapping
      
      final_confidence = base_confidence - language_penalty
      ```

12. **Czech Repair Loop Integration (CZ_REPAIR)** [Todo 22]
    - If Czech normalization produces unknown token, trigger targeted repair
    - Repair prompt includes Czech context:
      ```
      You used non-canonical Czech token "míra konverze" in output.
      Correct to canonical English: "conversion_rate"
      Return corrected JSON only.
      ```
    - Track repair success rate per language

13. **Fallback Translation Strategy (CZ_FALLBACK)** [Todo 29]
    - For low-confidence Czech classifications (<0.6 after normalization):
      - Option A: Use lightweight translation API (local Moses/Bergamot or external)
      - Option B: Prompt LLM to translate question to English, then classify
    - Map dimension values back if language-agnostic (e.g., "EMEA" stays)
    - Store both normalized and translated variants in metadata
    - Environment flag: `ENABLE_TRANSLATION_FALLBACK=true`

**Acceptance Criteria**
- Confidence scores correlate with accuracy (Spearman ρ > 0.6)
- Repair success rate: ≥80% for Czech normalization failures
- Fallback translation improves low-confidence cases by ≥10pp

### Phase 5.6: Performance & Observability (Week 3-4)
**Goal**: Minimize latency overhead; track language-specific metrics.

**Tasks**
14. **Language-Aware Caching (LANG_CACHE)** [Todo 26]
    - Cache normalized Czech questions → classification result
    - Cache key: `hash(normalized_question + prompt_hash + language)`
    - TTL: 1 hour (configurable)
    - Invalidation: on taxonomy version change
    - Expected cache hit rate: ≥70% for repeated Czech queries

15. **Multilingual Telemetry (ML_TELEMETRY)** [Todo 24]
    - Add fields to classification metadata:
      ```json
      {
        "language": "cs",
        "normalization_coverage": 0.95,
        "original_question": "Jaké jsou naše tržby?",
        "normalized_question": "What is our revenue?",
        "translation_fallback_used": false
      }
      ```
    - Emit per-language metrics:
      - Classification count by language
      - Accuracy by language & component
      - Normalization coverage distribution
      - Repair/fallback usage frequency
    - Dashboard: separate EN vs CZ trend lines

16. **Prompt Versioning + Locale Hash (PROMPT_VER_LOCALE)** [Todo 25]
    - Extend prompt_hash to include language variant
    - Hash components: base_prompt + language_section + taxonomy_version
    - Track in metadata: `{"prompt_hash": "abc123", "language_variant": "cs"}`
    - Enable regression tracking per language

**Acceptance Criteria**
- Cache hit rate: ≥70% Czech queries
- Telemetry dashboard shows EN/CZ split metrics
- Added latency with cache hit: <20ms
- Added latency cache miss: <100ms (detection + normalization)

### Phase 5.7: Retrieval & Advanced Features (Week 4)
**Goal**: Enhance accuracy via bilingual exemplars; prepare for ongoing improvement.

**Tasks**
17. **Czech Retrieval Exemplars (CZ_RETRIEVE)** [Todo 23]
    - Build bilingual exemplar store:
      - English questions → embeddings
      - Czech questions → embeddings
    - Retrieval strategy:
      1. First search: same-language exemplars (k=3)
      2. Fallback: if <k results, retrieve from English (translate query embedding)
    - Insert exemplars into prompt with language tag:
      ```
      Similar Czech examples:
      Q: "Jaký je náš MRR?" → {...}
      
      Similar English examples (fallback):
      Q: "What is our MRR?" → {...}
      ```
    - Measure accuracy uplift vs no retrieval

18. **Active Learning for Czech (CZ_ACTIVE)**
    - Queue low-confidence Czech classifications for human review
    - Criteria: confidence <0.6 OR normalization_coverage <0.8
    - Review interface shows:
      - Original Czech question
      - Normalized question
      - Current classification
      - Expected classification (human input)
    - Auto-add validated cases to gold set + taxonomy if new synonym found

**Acceptance Criteria**
- Retrieval improves Czech accuracy by ≥3pp on challenging cases
- Active learning queue processes ≥20 Czech cases/week
- Taxonomy enrichment: ≥5 new Czech synonyms added in first month

## 6. Implementation Order (Detailed)

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 1 | Detection (LANG_DETECT), Normalization (CZ_NORM), Taxonomy Extensions (CZ_TAXONOMY, CZ_DIM_SYN, CZ_TIME) | Language detector module, normalization map, extended taxonomy files |
| 2 | Prompt Adaptation (DUAL_PROMPT, PROMPT_MOD), Test Suite (CZ_TESTS) | Modular prompts, 80+ Czech test cases |
| 2-3 | Evaluation (CZ_EVAL), Confidence (CZ_CONF), Repair (CZ_REPAIR) | Czech eval harness, calibrated confidence, repair integration |
| 3 | Fallback Translation (CZ_FALLBACK), Caching (LANG_CACHE) | Translation fallback, language-aware cache |
| 3-4 | Telemetry (ML_TELEMETRY), Versioning (PROMPT_VER_LOCALE) | Multilingual dashboard, versioned prompts |
| 4 | Retrieval (CZ_RETRIEVE), Active Learning (CZ_ACTIVE) | Bilingual exemplar store, active learning queue |

## 7. Deliverables

### Code Components
- `backend/lambda/detection/language_detector.py` - Fast Czech/English detection
- `backend/lambda/normalization/cz_normalizer.py` - Czech → English token mapper
- `backend/lambda/normalization/cz_mapping.json` - Translation dictionary (diacritic-free keys)
- `backend/lambda/normalization/diacritic_utils.py` - Diacritic stripping utility
- `backend/lambda/prompts/classification/prompt_base.txt` - Core schema
- `backend/lambda/prompts/classification/prompt_examples_cs.txt` - Czech examples (with/without diacritics)
- `taxonomy/subjects/*.json` - Extended with Czech translations (both variants)
- `taxonomy/shared/dimensions.json` - Czech dimension synonyms (both variants)
- `taxonomy/shared/time.json` - Czech time tokens (both variants)

### Test Artifacts
- `backend/tests/data/product_owner_questions_cz.csv` - 80-100 Czech test cases
- `backend/tests/e2e/test_product_owner_questions_cz.py` - Czech test suite
- `backend/tests/lambda/test_language_detector.py` - Detection unit tests
- `backend/tests/lambda/test_cz_normalizer.py` - Normalization unit tests

### Documentation
- `docs/MULTILINGUAL_GUIDE.md` - Usage & architecture guide
- `backend/lambda/README.md` - Updated with Czech env vars
- `DEVELOPMENT_PLAN.md` - Phase 5 completion notes
- Taxonomy README with translation contribution guidelines

## 8. Environment Variables

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `ENABLE_LANG_DETECT` | Enable language detection | `false` | `true` |
| `ENABLE_TRANSLATION_FALLBACK` | Use translation for low-confidence | `false` | `true` |
| `LANGUAGE_EXEMPLARS_DIR` | Path to bilingual exemplar store | `null` | `/opt/exemplars` |
| `CZ_NORMALIZATION_MAP_PATH` | Override default mapping file | `normalization/cz_mapping.json` | Custom path |
| `LANG_DETECT_CONFIDENCE_THRESHOLD` | Min confidence for detection | `0.8` | `0.9` |
| `ENABLE_LANG_CACHE` | Enable language-aware caching | `true` | `true` |

## 9. Acceptance Criteria (Czech Support)

### Functional Requirements
- ✅ Czech questions correctly classified with canonical English output tokens
- ✅ **MANDATORY**: Diacritic-free Czech text processed with same accuracy as diacritic text
- ✅ Language detection accuracy ≥98% (both diacritic and diacritic-free)
- ✅ Normalization coverage ≥90% common phrases (both variants)
- ✅ All 12 subjects + shared dimensions have Czech translations (both diacritic and diacritic-free aliases)
- ✅ Czech test suite (≥80 questions, 50% diacritic-free) runs successfully

### Quality Requirements
- ✅ CZ intent accuracy ≥95% (within 3pp of EN)
- ✅ CZ subject accuracy ≥95% (within 3pp of EN)
- ✅ CZ measure accuracy ≥93% (within 3pp of EN)
- ✅ CZ dimension accuracy ≥89% (within 3pp of EN)
- ✅ CZ time accuracy ≥92% (within 3pp of EN)
- ✅ No raw Czech tokens in output JSON
- ✅ Confidence scores calibrated per language

### Performance Requirements
- ✅ Language detection latency <10ms p95
- ✅ Normalization latency <50ms p95
- ✅ Total added overhead <100ms p95
- ✅ Cache hit rate ≥70% for repeated Czech queries

### Observability Requirements
- ✅ Per-language metrics emitted (classification count, accuracy, latency)
- ✅ Normalization coverage tracked
- ✅ Repair/fallback usage monitored
- ✅ Dashboard shows EN vs CZ trends

## 10. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Incomplete normalization coverage** | Low accuracy on unmapped phrases | Active learning queue; regular taxonomy updates; fallback translation |
| **Detection ambiguity (short queries)** | Wrong language assumed | Embedding fallback; confidence threshold; manual override in API |
| **Czech-specific grammar nuances** | Misclassification of complex sentences | Prompt examples covering edge cases; self-repair for known patterns |
| **Performance degradation** | Latency spikes on Czech queries | Caching; pre-compilation of normalization maps; async detection |
| **Taxonomy maintenance overhead** | Translations fall out of sync | Automated validation in CI; translation review workflow |
| **Model bias toward English** | Lower Czech accuracy despite normalization | Bilingual prompt examples; active learning to enrich Czech dataset |

## 11. Success Metrics (30-Day Post-Launch)

- Czech classification volume ≥20% total traffic
- CZ accuracy deltas within target (<3pp all components)
- Zero critical failures (parse errors, wrong language detection)
- Cache hit rate ≥70%
- Active learning queue processed ≥50 cases
- Taxonomy enriched with ≥10 new Czech synonyms
- User satisfaction: ≥90% positive feedback on Czech accuracy

## 12. Next Steps After Czech Launch

1. **Additional Languages**: Slovak (similar to Czech), Polish (partial reuse)
2. **Regional Dialects**: Support for regional business terminology
3. **Domain-Specific Vocabularies**: Industry-specific metric translations
4. **Automated Translation Updates**: CI pipeline for keeping translations in sync
5. **Multilingual Retrieval**: Cross-language exemplar matching for rare queries

---

**Status**: Ready for implementation. Begin with Phase 5.1 (Detection & Normalization).
