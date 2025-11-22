#!/usr/bin/env python3
"""Czech Alias Governance Tool

Validates, deduplicates, and reports on Czech lexicon aliases.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "lambda"))

from normalization.diacritic_utils import strip_diacritics

LEXICON_DIR = Path(__file__).parent.parent / "lambda" / "normalization" / "lexicons"


def load_lexicon(filename: str) -> Dict[str, List[str]]:
    """Load a single lexicon file."""
    path = LEXICON_DIR / filename
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_lexicon(filename: str, data: Dict[str, List[str]]) -> None:
    """Save a lexicon file with pretty formatting."""
    path = LEXICON_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_alias(alias: str) -> str:
    """Normalize an alias: strip diacritics and lowercase."""
    return strip_diacritics(alias.strip().lower())


def validate_lexicon(filename: str) -> Tuple[List[str], List[str], Dict[str, List[str]]]:
    """Validate a lexicon file.
    
    Returns:
        (errors, warnings, duplicates_by_canonical)
    """
    data = load_lexicon(filename)
    errors = []
    warnings = []
    duplicates: Dict[str, List[str]] = {}
    
    # Track normalized aliases across all canonicals
    seen_normalized: Dict[str, str] = {}  # normalized -> canonical
    
    for canonical, aliases in data.items():
        if not isinstance(aliases, list):
            errors.append(f"{filename}:{canonical} - aliases must be a list")
            continue
        
        # Check for duplicates within this canonical's aliases
        normalized_set: Set[str] = set()
        for alias in aliases:
            normalized = normalize_alias(alias)
            
            # Check for duplicate within same canonical
            if normalized in normalized_set:
                if canonical not in duplicates:
                    duplicates[canonical] = []
                duplicates[canonical].append(alias)
            else:
                normalized_set.add(normalized)
            
            # Check for duplicate across canonicals
            if normalized in seen_normalized:
                other_canonical = seen_normalized[normalized]
                warnings.append(
                    f"{filename}: '{alias}' ({normalized}) appears in both "
                    f"'{canonical}' and '{other_canonical}'"
                )
            else:
                seen_normalized[normalized] = canonical
            
            # Check for diacritics (should be diacritic-free)
            if normalized != alias.strip().lower():
                warnings.append(
                    f"{filename}:{canonical} - alias '{alias}' contains diacritics"
                )
    
    return errors, warnings, duplicates


def deduplicate_lexicon(filename: str, dry_run: bool = True) -> Dict[str, Any]:
    """Remove duplicate aliases from a lexicon.
    
    Args:
        filename: Lexicon file to process
        dry_run: If True, only report changes without saving
    
    Returns:
        Report dict with changes made
    """
    data = load_lexicon(filename)
    changes = {"removed": 0, "aliases_by_canonical": {}}
    
    for canonical, aliases in data.items():
        seen_normalized: Set[str] = set()
        unique_aliases = []
        
        for alias in aliases:
            normalized = normalize_alias(alias)
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                unique_aliases.append(alias)
            else:
                changes["removed"] += 1
                if canonical not in changes["aliases_by_canonical"]:
                    changes["aliases_by_canonical"][canonical] = []
                changes["aliases_by_canonical"][canonical].append(alias)
        
        data[canonical] = unique_aliases
    
    if not dry_run and changes["removed"] > 0:
        save_lexicon(filename, data)
    
    return changes


def diff_lexicon(old_filename: str, new_filename: str) -> Dict[str, Any]:
    """Compare two lexicon files and report differences.
    
    Args:
        old_filename: Original lexicon
        new_filename: Updated lexicon
    
    Returns:
        Report dict with additions, deletions, modifications
    """
    old_data = load_lexicon(old_filename)
    new_data = load_lexicon(new_filename)
    
    old_canonicals = set(old_data.keys())
    new_canonicals = set(new_data.keys())
    
    report = {
        "added_canonicals": sorted(new_canonicals - old_canonicals),
        "removed_canonicals": sorted(old_canonicals - new_canonicals),
        "modified_canonicals": {},
    }
    
    for canonical in old_canonicals & new_canonicals:
        old_aliases = set(normalize_alias(a) for a in old_data[canonical])
        new_aliases = set(normalize_alias(a) for a in new_data[canonical])
        
        added = new_aliases - old_aliases
        removed = old_aliases - new_aliases
        
        if added or removed:
            report["modified_canonicals"][canonical] = {
                "added": sorted(added),
                "removed": sorted(removed),
            }
    
    return report


def main():
    """Run governance checks on all lexicons."""
    lexicon_files = [
        "subjects_cs.json",
        "metrics_cs.json",
        "intents_cs.json",
        "time_periods_cs.json",
        "time_windows_cs.json",
        "dimensions_cs.json",
        "granularity_cs.json",
    ]
    
    print("🔍 Czech Lexicon Governance Report\n")
    
    all_errors = []
    all_warnings = []
    all_duplicates = {}
    
    for filename in lexicon_files:
        errors, warnings, duplicates = validate_lexicon(filename)
        
        if errors or warnings or duplicates:
            print(f"📄 {filename}")
            
            if errors:
                for error in errors:
                    print(f"  ❌ ERROR: {error}")
                all_errors.extend(errors)
            
            if warnings:
                for warning in warnings:
                    print(f"  ⚠️  WARNING: {warning}")
                all_warnings.extend(warnings)
            
            if duplicates:
                for canonical, dupes in duplicates.items():
                    print(f"  🔁 DUPLICATE in '{canonical}': {dupes}")
                all_duplicates[filename] = duplicates
            
            print()
    
    # Summary
    print("=" * 60)
    print(f"Total errors: {len(all_errors)}")
    print(f"Total warnings: {len(all_warnings)}")
    print(f"Files with duplicates: {len(all_duplicates)}")
    
    if all_errors:
        sys.exit(1)
    else:
        print("\n✅ All lexicons validated successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
