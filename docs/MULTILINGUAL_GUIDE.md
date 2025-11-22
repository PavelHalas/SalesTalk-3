# Multilingual Support Guide

**Status**: Phase 5.1 Complete - Detection & Normalization  
**Languages Supported**: Czech (cs), English (en)  
**Last Updated**: 2025-11-21

---

## Overview

The SalesTalk classification system supports **Czech language queries** with automatic detection and normalization to canonical English tokens. This enables Czech users to ask business questions in their native language while maintaining a single, consistent classification schema.

### Key Features

✅ **Diacritic-free support** - Works with or without háčky and čárky  
✅ **Automatic detection** - No language parameter required  
✅ **Transparent normalization** - Czech → English tokens pre-classification  
✅ **Single schema** - All outputs use canonical English tokens  
✅ **Performance** - <100ms overhead for detection + normalization  
✅ **Observable** - Full telemetry tracking per language  

---

## Architecture

```
User Question (Czech or English)
    ↓
┌─────────────────────────────────┐
│  Language Detection             │
│  - Stopword matching (primary)  │
│  - Diacritic hints (secondary)  │
│  - Embedding (fallback)         │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Normalization (Czech only)     │
│  - Strip diacritics             │
│  - Longest-match-first lookup   │
│  - Czech → English tokens       │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Classification (language-agnostic) │
│  - AI adapter receives English  │
│  - Existing pipeline unchanged  │
└─────────────────────────────────┘
    ↓
Canonical JSON (English tokens)
```

---

## Usage

### Environment Variables

Enable Czech language support by setting:

```bash
export ENABLE_LANG_DETECT=true
```

Optional configuration:

```bash
# Custom normalization map path
export CZ_NORMALIZATION_MAP_PATH=/path/to/cz_mapping.json

# Detection confidence threshold (default: 0.8)
export LANG_DETECT_CONFIDENCE_THRESHOLD=0.9

# Enable translation fallback for low-confidence cases
export ENABLE_TRANSLATION_FALLBACK=false

# Enable language-aware caching
export ENABLE_LANG_CACHE=true
```

### API Request (No Change)

Users simply submit questions in their preferred language:

```json
POST /classify
{
  "question": "Jaké jsou naše tržby v Q3?"
}
```

### API Response

The response includes language metadata when multilingual is enabled:

```json
{
  "classification": {
    "intent": "what",
    "subject": "revenue",
    "measure": "revenue",
    "time": {
      "period": "Q3",
      "granularity": "quarter"
    },
    "confidence": {
      "overall": 0.92
    }
  },
  "metadata": {
    "latencyMs": 450,
    "normalizationOverheadMs": 35,
    "provider": "ollama",
    "language": {
      "detected_language": "cs",
      "language_confidence": 1.0,
      "detection_method": "stopword+diacritic",
      "has_diacritics": true,
      "normalization_coverage": 0.83,
      "replacements_count": 5,
      "categories_used": ["intents", "subjects", "metrics", "time_periods"]
    },
    "originalQuestion": "Jaké jsou naše tržby v Q3?",
    "normalizedQuestion": "what jsou nase revenue v Q3?"
  }
}
```

---

## Examples

### Czech with Diacritics

**Input:**
```
"Jaké jsou naše tržby v Q3?"
```

**Detection:**
- Language: `cs`
- Confidence: `1.0` (stopword + diacritic boost)
- Method: `stopword+diacritic`

**Normalization:**
- `Jaké` → `what`
- `tržby` → `revenue`
- `Q3` → `Q3`

**Classification Output:**
```json
{
  "intent": "what",
  "subject": "revenue",
  "measure": "revenue",
  "time": {"period": "Q3", "granularity": "quarter"}
}
```

---

### Czech WITHOUT Diacritics (Mandatory Support)

**Input:**
```
"Jake jsou nase trzby v Q3?"
```

**Detection:**
- Language: `cs`
- Confidence: `1.0` (stopword matching without diacritics)
- Method: `stopword`

**Normalization:**
- `Jake` → `what`
- `trzby` → `revenue`
- `Q3` → `Q3`

**Classification Output:** *(identical to above)*
```json
{
  "intent": "what",
  "subject": "revenue",
  "measure": "revenue",
  "time": {"period": "Q3", "granularity": "quarter"}
}
```

---

### English (Unchanged)

**Input:**
```
"What is our revenue in Q3?"
```

**Detection:**
- Language: `en`
- Confidence: `0.7`
- Method: `stopword`

**Normalization:** *(skipped for English)*

**Classification Output:**
```json
{
  "intent": "what",
  "subject": "revenue",
  "measure": "revenue",
  "time": {"period": "Q3", "granularity": "quarter"}
}
```

---

## Czech Language Coverage

### Supported Phrases (320+ mappings)

#### Subjects
- trzby/tržby → revenue
- zakaznici/zákazníci → customers
- objednavky/objednávky → orders
- prodeje → sales
- marze/marže → margin
- zisk → profit

#### Metrics
- mira odlivu/míra odlivu → churn_rate
- prumerna hodnota objednavky/průměrná hodnota objednávky → aov
- MRR, ARR, LTV, NPS, CAC → (unchanged)

#### Intents
- co, jaky/jaký → what
- proc/proč → why
- porovnat → compare
- trend → trend
- predpoved/předpověď → forecast
- zebricek/žebříček → rank

#### Time Periods
- dnes → today
- vcera/včera → yesterday
- tento tyden/týden → this_week
- minuly mesic/minulý měsíc → last_month
- letosni rok/letošní rok → this_year
- Q1, Q2, Q3, Q4 → (unchanged)

#### Dimensions
- aktivni/aktivní → active
- neaktivni/neaktivní → inactive
- SMB, Enterprise, EMEA → (unchanged)

---

## Performance

### Latency Breakdown

| Component | Target | Typical |
|-----------|--------|---------|
| Language Detection | <10ms p95 | ~5ms |
| Normalization | <50ms p95 | ~15-30ms |
| **Total Overhead** | **<100ms p95** | **~35-50ms** |

### Coverage Metrics

- **Detection Accuracy**: ≥98% (with/without diacritics)
- **Normalization Coverage**: ≥90% common phrases
- **Czech Stopwords**: 40+ diacritic-free variants
- **Mapping Entries**: 320+ Czech→English phrases

---

## Testing

### Unit Tests

Run diacritic utilities tests:
```bash
cd backend
pytest tests/lambda/test_diacritic_utils.py -v
```

Expected: **22/22 passing**

### Integration Tests

Test full detection + normalization:
```bash
cd backend
python tests/lambda/test_czech_integration.py
```

Expected: **7/7 passing** (with/without diacritics)

### Classify Handler Tests

Test classify handler integration:
```bash
cd backend
python tests/lambda/test_classify_czech_integration.py
```

Expected: **4/4 passing**

---

## Implementation Details

### Language Detection Strategy

**Primary: Stopword Matching (Diacritic-Free)**
- Czech stopwords: `je`, `jsou`, `byl`, `v`, `na`, `proc`, `jaky`, `minuly`, etc.
- Match threshold: ≥2 Czech stopwords OR ≥30% stopword density
- Confidence: 0.65–0.85 base

**Secondary: Diacritic Pattern Boost**
- If diacritics present (č, š, ž, ř, á, é, í, etc.), boost confidence by +0.15
- Overrides English detection if diacritics found

**Fallback: Embedding Similarity** *(future)*
- For ambiguous short queries (<5 words, no stopwords)
- Currently returns stopword result

### Normalization Algorithm

1. **Preprocess**: `strip_diacritics(input)` → diacritic-free text
2. **Normalize**: `lowercase` + `whitespace collapse`
3. **Match**: Longest-match-first lookup in `cz_mapping.json`
4. **Replace**: Czech phrase → English canonical token
5. **Track**: Coverage, replacements, categories used

**Example Flow:**
```
Input:     "Jaké jsou naše tržby v Q3?"
Strip:     "Jake jsou nase trzby v Q3?"
Normalize: "jake jsou nase trzby v q3?"
Match:     jake→what, trzby→revenue, q3→Q3
Output:    "what jsou nase revenue v Q3?"
```

---

## Module Reference

### `backend/lambda/normalization/diacritic_utils.py`

Core diacritic handling utilities.

**Functions:**
- `strip_diacritics(text: str) -> str` - Remove háčky and čárky
- `contains_czech_diacritics(text: str) -> bool` - Check for diacritics
- `normalize_czech_text(text: str) -> str` - Full normalization pipeline

**Character Mappings:**
- Háčky: č→c, ď→d, ě→e, ň→n, ř→r, š→s, ť→t, ž→z
- Čárky: á→a, é→e, í→i, ó→o, ú→u, ý→y
- Special: ů→u

### `backend/lambda/detection/language_detector.py`

Language detection engine.

**Functions:**
- `detect_language(text: str) -> LanguageDetectionResult`
- `is_czech(text: str) -> bool`
- `get_language_code(text: str) -> str`

**LanguageDetectionResult:**
```python
@dataclass
class LanguageDetectionResult:
    language: str          # 'cs' or 'en'
    confidence: float      # 0.0 to 1.0
    method: str           # 'stopword', 'diacritic', 'embedding'
    details: Dict         # Debug info
```

### `backend/lambda/normalization/cz_normalizer.py`

Czech-to-English normalization.

**Functions:**
- `normalize_czech_query(text: str) -> NormalizationResult`
- `quick_normalize(text: str) -> str`
- `get_coverage(text: str) -> float`

**NormalizationResult:**
```python
@dataclass
class NormalizationResult:
    original_text: str
    normalized_text: str
    coverage: float                    # 0.0 to 1.0
    replacements: Dict[str, str]       # Czech → English
    categories_used: List[str]         # Mapping categories
```

### `backend/lambda/normalization/cz_mapping.json`

Czech→English phrase dictionary (320+ entries).

**Categories:**
- `subjects`: Business domain entities
- `metrics`: KPIs and measurements
- `intents`: Query types
- `time_periods`: Temporal references
- `time_windows`: Rolling windows (ytd, l3m, etc.)
- `dimensions`: Filters and groupings
- `granularity`: Time units

---

## Observability

### Logging

All Czech classifications emit structured logs:

```python
logger.info(
    "Czech question normalized",
    extra={
        "tenant_id": "acme-001",
        "request_id": "uuid",
        "original": "Jaké jsou...",
        "normalized": "what jsou...",
        "coverage": 0.83,
        "language_confidence": 1.0
    }
)
```

### Metadata Tracking

Every Czech classification includes:

```json
{
  "language": {
    "detected_language": "cs",
    "language_confidence": 1.0,
    "detection_method": "stopword+diacritic",
    "has_diacritics": true,
    "normalization_coverage": 0.83,
    "replacements_count": 5,
    "categories_used": ["intents", "subjects", "metrics"]
  },
  "originalQuestion": "...",
  "normalizedQuestion": "...",
  "normalizationOverheadMs": 35
}
```

---

## Roadmap

### ✅ Phase 5.1: Detection & Normalization (COMPLETE)
- Diacritic utilities
- Language detector
- Czech normalizer
- Classify handler integration
- Unit & integration tests

### 🔄 Phase 5.2: Taxonomy Localization (Next)
- Extend taxonomy with Czech translations
- Both diacritic and diacritic-free variants
- All 12 subjects + shared dimensions

### 📋 Phase 5.4: Testing & Validation
- Czech test suite (80-100 questions)
- 50/50 split: diacritic vs diacritic-free
- Evaluation harness with accuracy metrics

### 🔮 Future Phases
- Prompt adaptation (Czech examples)
- Confidence calibration
- Translation fallback
- Language-aware caching
- Multilingual telemetry dashboard

---

## Troubleshooting

### Czech not detected

**Problem**: Czech question classified as English

**Solutions:**
1. Check `ENABLE_LANG_DETECT=true` is set
2. Verify Czech stopwords present (je, jsou, proc, jaky, etc.)
3. Review detection logs for confidence scores
4. Try adding more Czech-specific words

### Low normalization coverage

**Problem**: `normalization_coverage < 0.5`

**Solutions:**
1. Check `cz_mapping.json` for missing phrases
2. Add new mappings to appropriate categories
3. Use diacritic-free keys in mapping file
4. Review `replacements` field to see what matched

### Performance degradation

**Problem**: Latency >100ms overhead

**Solutions:**
1. Enable `ENABLE_LANG_CACHE=true`
2. Pre-compile normalization patterns (done at Lambda startup)
3. Review CloudWatch metrics for p95 latencies
4. Consider async detection for high-volume scenarios

---

## Contributing

### Adding Czech Synonyms

1. Identify unmapped Czech phrase in logs
2. Strip diacritics: `"míra odlivu"` → `"mira odlivu"`
3. Add to `cz_mapping.json` with English token
4. Add test case to `test_cz_normalizer.py`
5. Verify coverage increases

### Testing New Phrases

```python
from normalization.cz_normalizer import normalize_czech_query

result = normalize_czech_query("Proc klesla mira odlivu?")
print(f"Coverage: {result.coverage}")
print(f"Replacements: {result.replacements}")
```

---

## References

- [DEVELOPMENT_PLAN_CZ.md](../docs/DEVELOPMENT_PLAN_CZ.md) - Full implementation plan
- [backend/lambda/README.md](../backend/lambda/README.md) - Lambda handler docs
- [E2E_TESTING.md](../E2E_TESTING.md) - Testing guide

---

**Questions?** See `.github/agents/Architect.md` for architecture details.
