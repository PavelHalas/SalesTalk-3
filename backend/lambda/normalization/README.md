# Czech Normalization Lexicons

This directory contains the per-category Czech → English normalization lexicons and supporting loaders used by the classification pipeline.

## Structure
- `lexicons/`
  - One file per category. Each file maps canonical English tokens to an array of Czech aliases.
  - Files: `subjects_cs.json`, `metrics_cs.json`, `intents_cs.json`, `time_periods_cs.json`, `time_windows_cs.json`, `dimensions_cs.json`, `granularity_cs.json`.
- `lexicon_loader.py`
  - Loads lexicon files and produces a flattened mapping: `category -> { cz_alias -> canonical_en }`.
  - Aliases are lowercased and diacritics are stripped for deduplication.
- `cz_normalizer.py`
  - Builds longest‑match‑first regexes from the flattened mapping and performs replacements on diacritic‑free text.
  - Also supports colloquial templates via `patterns_cz.json` and fuzzy fallback.

## Design principles
- Diacritic‑free processing: All aliases are matched without diacritics; do not duplicate diacritic variants.
- Category ownership: Add or modify aliases only in the relevant `lexicons/*.json` file.
- Deterministic normalization: Longest‑match‑first per category to keep results stable and predictable.
- Backward compatibility: Legacy `cz_mapping.json` has been removed. If reintroduced, it would be merged after lexicons but should remain empty.

## Adding aliases
1. Choose the right category file under `lexicons/`.
2. Add the Czech alias to the proper canonical English token list.
3. Keep aliases lowercased and without diacritics (the pipeline strips diacritics at runtime).
4. Avoid ambiguous short tokens that could over‑match (prefer longer n‑grams).
5. Run the tests.

## Tests
From `backend/`:

```bash
pytest tests/lambda/test_czech_integration.py -q
pytest tests/lambda/test_classify_czech_integration.py -q
pytest tests/lambda/test_pattern_matcher.py -q
pytest tests/lambda/test_fuzzy_matcher.py -q
```

## Notes
- Conflicts: If two canonical tokens share the same alias, the last one wins in the loader. Prefer distinct aliases.
- Granularity: Avoid reusing the same alias for both `week` and `weekly` (see `granularity_cs.json`).
