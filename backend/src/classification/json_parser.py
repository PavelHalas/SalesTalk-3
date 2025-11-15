"""
Phase 0: Strict JSON Parser (JSON_STRICT)

Provides robust JSON parsing with automatic recovery and re-prompting
for malformed responses. Includes streaming brace balancing.
"""

import json
import re
from typing import Dict, Any, Optional, Tuple


def extract_json_strict(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract JSON from text with multiple fallback strategies.
    
    Args:
        text: Raw text that should contain JSON
        
    Returns:
        Tuple of (parsed_json_dict or None, error_message or None)
    """
    if not text:
        return None, "Empty text provided"
    
    text = text.strip()
    
    # Strategy 1: Try direct parse
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Remove markdown code blocks
    cleaned = text
    if "```json" in text:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
    elif "```" in text:
        match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
    
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Find first { to last }
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_candidate = cleaned[first_brace:last_brace + 1]
        try:
            return json.loads(json_candidate), None
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Balance braces (add missing closing braces)
    balanced, was_fixed = balance_braces(cleaned)
    if was_fixed:
        try:
            return json.loads(balanced), None
        except json.JSONDecodeError:
            pass
    
    # Strategy 5: Try to find JSON-like structure and fix common issues
    fixed = fix_common_json_errors(cleaned)
    if fixed != cleaned:
        try:
            return json.loads(fixed), None
        except json.JSONDecodeError:
            pass
    
    # All strategies failed
    return None, f"Failed to parse JSON after multiple strategies. Text length: {len(text)}"


def balance_braces(text: str) -> Tuple[str, bool]:
    """
    Balance braces in JSON text by adding missing closing braces.
    
    Args:
        text: Potentially malformed JSON text
        
    Returns:
        Tuple of (balanced_text, was_modified)
    """
    # Find the JSON object boundaries
    first_brace = text.find('{')
    if first_brace == -1:
        return text, False
    
    # Count braces
    open_count = 0
    close_count = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[first_brace:], start=first_brace):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                open_count += 1
            elif char == '}':
                close_count += 1
    
    # Add missing closing braces
    if open_count > close_count:
        missing = open_count - close_count
        return text + ('}' * missing), True
    
    return text, False


def fix_common_json_errors(text: str) -> str:
    """
    Fix common JSON formatting errors.
    
    Args:
        text: JSON text with potential errors
        
    Returns:
        Fixed JSON text
    """
    # Find JSON boundaries
    first_brace = text.find('{')
    if first_brace == -1:
        return text
    
    # Get just the JSON part
    json_part = text[first_brace:]
    
    # Fix trailing commas before closing braces/brackets
    json_part = re.sub(r',(\s*[}\]])', r'\1', json_part)
    
    # Fix single quotes to double quotes (risky but common error)
    # Only do this outside of already-quoted strings
    # Simple heuristic: replace single quotes around words
    json_part = re.sub(r"'([^'\"]*)'(\s*:)", r'"\1"\2', json_part)  # keys
    json_part = re.sub(r":\s*'([^'\"]*)'", r': "\1"', json_part)  # string values
    
    # Remove any trailing text after the last }
    last_brace = json_part.rfind('}')
    if last_brace != -1:
        json_part = json_part[:last_brace + 1]
    
    return text[:first_brace] + json_part


def validate_classification_structure(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate that parsed JSON has the expected classification structure.
    
    Args:
        data: Parsed JSON dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["intent", "subject", "measure", "confidence"]
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate confidence structure
    confidence = data.get("confidence")
    if not isinstance(confidence, dict):
        return False, "confidence must be a dictionary"
    
    if "overall" not in confidence:
        return False, "confidence.overall is required"
    
    overall = confidence.get("overall")
    if not isinstance(overall, (int, float)):
        return False, f"confidence.overall must be numeric, got {type(overall)}"
    
    if not (0.0 <= overall <= 1.0):
        return False, f"confidence.overall must be in [0.0, 1.0], got {overall}"
    
    # Validate component confidences if present
    components = confidence.get("components", {})
    if components:
        for key, value in components.items():
            if not isinstance(value, (int, float)):
                return False, f"confidence.components.{key} must be numeric"
            if not (0.0 <= value <= 1.0):
                return False, f"confidence.components.{key} must be in [0.0, 1.0], got {value}"
    
    return True, ""


def count_parse_attempts(text: str) -> int:
    """
    Count how many parsing strategies were needed.
    Used for metrics tracking.
    
    Args:
        text: The text that was parsed
        
    Returns:
        Number of strategies tried (1-5)
    """
    # This is a simplified version - in practice would be tracked during parsing
    if not text:
        return 0
    
    # Try each strategy in order
    text = text.strip()
    
    # Strategy 1: Direct parse
    try:
        json.loads(text)
        return 1
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Markdown removal
    cleaned = text
    if "```" in text:
        if "```json" in text:
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        else:
            match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        
        if match:
            cleaned = match.group(1).strip()
            try:
                json.loads(cleaned)
                return 2
            except json.JSONDecodeError:
                pass
    
    # Strategy 3: Brace extraction
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    if first_brace != -1 and last_brace != -1:
        try:
            json.loads(cleaned[first_brace:last_brace + 1])
            return 3
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Brace balancing
    balanced, was_fixed = balance_braces(cleaned)
    if was_fixed:
        try:
            json.loads(balanced)
            return 4
        except json.JSONDecodeError:
            pass
    
    # Strategy 5: Error fixing
    fixed = fix_common_json_errors(cleaned)
    try:
        json.loads(fixed)
        return 5
    except json.JSONDecodeError:
        pass
    
    # Failed all strategies
    return 5
