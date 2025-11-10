# Adversarial Tests

## Purpose

Adversarial tests are designed to **falsify assumptions** and discover edge cases in the SalesTalk question-processing pipeline. These tests intentionally push boundaries and test robustness under challenging inputs.

## Philosophy

- **Falsify first:** Try to break assumptions before proving them
- **Edge-case heavy:** Design tests where optimism fails
- **Known-gaps visible:** Track failing tests with rationale, not to shame
- **Non-determinism aware:** Test AI behavior within tolerance windows

## Test Categories

### Typo Robustness (`TestTypoRobustness`)

Tests handling of common typos and misspellings:
- Single letter typos (reveneu → revenue)
- Missing vowels (rvnue → revenue)
- Letter transpositions (revnue → revenue)
- Letter swaps (reveune → revenue)

**Known Gap:** Spell correction not implemented - tracked for v1.1

### Mixed Locales (`TestMixedLocaleRobustness`)

Tests handling of:
- Emoji characters (💰)
- Code-switching between languages
- ALL CAPS input
- Excessive punctuation
- Unicode special characters (Δ)

### Ambiguous Time Handling (`TestAmbiguousTimeHandling`)

Tests temporal reasoning with:
- Relative time phrases (last quarter, this quarter)
- Vague future references
- Invalid periods (Q15)
- DST boundaries (known gap for v1.2)

### Edge Case Inputs (`TestEdgeCaseInputs`)

Tests extreme inputs:
- Empty strings
- Whitespace-only
- Single words
- Extremely long questions
- Emoji-only input

### Adversarial Dataset Integration (`TestAdversarialDataset`)

Leverages `backend/evaluation/adversarial.json` with 35 challenging questions across categories:
- typo
- emoji
- all_caps
- noise
- incomplete_syntax
- multi_question
- vague
- nonsense

## Known Gaps

All known gaps are tracked with `@pytest.mark.xfail` or `@pytest.mark.skip` including:

| Gap | Rationale | ETA |
|-----|-----------|-----|
| Spell correction | Not in MVP scope | v1.1 |
| Multi-language support | Out of MVP scope | v2.0 |
| DST boundary handling | Complex temporal logic | v1.2 |
| Hypothetical scenarios | Not in product scope | No ETA |

## Running Tests

```bash
# Run all adversarial tests
pytest tests/adversarial/ -v

# Run specific categories
pytest tests/adversarial/test_fuzz.py::TestTypoRobustness -v

# Show skipped tests and reasons
pytest tests/adversarial/ -v -rs

# Show xfail tests
pytest tests/adversarial/ -v -rx
```

## Adding New Tests

When adding adversarial tests:

1. **Document the attack vector** - What assumption are you testing?
2. **Include rationale** - Why is this scenario important?
3. **Tag known gaps** - Use `@pytest.mark.xfail` with reason and ETA
4. **Add to adversarial.json** - Update the dataset if applicable
5. **Verify isolation** - Ensure tests don't affect each other

## Test Data

Adversarial test data is maintained in:
- `backend/evaluation/adversarial.json` - Curated edge cases
- Test fixtures in test files themselves

## Metrics

Track these metrics over time:
- Pass rate (excluding known gaps)
- Flake rate (should be 0%)
- Number of known gaps (should decrease)
- Coverage of adversarial categories

---

**Last Updated:** 2025-11-09  
**Maintainer:** Tester Copilot
