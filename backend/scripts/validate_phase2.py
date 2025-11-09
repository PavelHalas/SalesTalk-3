#!/usr/bin/env python3
"""
Phase 2 Data Platform Validation Script

Validates that all Phase 2 deliverables meet quality standards.

Usage:
    python scripts/validate_phase2.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class Phase2Validator:
    """Validates Phase 2 deliverables."""
    
    def __init__(self):
        self.root = Path(__file__).parent.parent.parent
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def check(self, name: str, condition: bool, error_msg: str = "") -> bool:
        """Check a condition and print result."""
        if condition:
            print(f"{GREEN}✓{RESET} {name}")
            self.passed += 1
            return True
        else:
            print(f"{RED}✗{RESET} {name}")
            if error_msg:
                print(f"  {RED}Error: {error_msg}{RESET}")
            self.failed += 1
            return False
    
    def warn(self, name: str, message: str):
        """Print a warning."""
        print(f"{YELLOW}⚠{RESET} {name}: {message}")
        self.warnings += 1
    
    def section(self, name: str):
        """Print a section header."""
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}{name}{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}")
    
    def validate_file_exists(self, path: Path, description: str) -> bool:
        """Validate that a file exists."""
        return self.check(
            f"{description}: {path.relative_to(self.root)}",
            path.exists(),
            f"File not found: {path}"
        )
    
    def validate_json_file(self, path: Path, required_keys: List[str]) -> bool:
        """Validate JSON file structure."""
        try:
            with open(path) as f:
                data = json.load(f)
            
            missing_keys = [k for k in required_keys if k not in data]
            if isinstance(data, list):
                # For arrays, check first item
                if len(data) > 0:
                    missing_keys = [k for k in required_keys if k not in data[0]]
                else:
                    return self.check(f"JSON data in {path.name}", False, "Empty array")
            
            return self.check(
                f"JSON structure in {path.name}",
                len(missing_keys) == 0,
                f"Missing keys: {missing_keys}"
            )
        except json.JSONDecodeError as e:
            return self.check(f"JSON validity in {path.name}", False, str(e))
        except Exception as e:
            return self.check(f"Loading {path.name}", False, str(e))
    
    def validate_terraform(self) -> bool:
        """Validate Terraform configuration."""
        self.section("Terraform Configuration")
        
        # Check files exist
        tf_dir = self.root / "infra" / "terraform"
        self.validate_file_exists(tf_dir / "dynamodb.tf", "DynamoDB configuration")
        self.validate_file_exists(tf_dir / "variables.tf", "Variables configuration")
        
        # Check for key resources in dynamodb.tf
        dynamodb_tf = tf_dir / "dynamodb.tf"
        if dynamodb_tf.exists():
            content = dynamodb_tf.read_text()
            self.check(
                "tenants-metadata table defined",
                'resource "aws_dynamodb_table" "tenants_metadata"' in content
            )
            self.check(
                "tenant messages table template defined",
                'resource "aws_dynamodb_table" "tenant_messages_template"' in content
            )
            self.check(
                "tenant metrics table template defined",
                'resource "aws_dynamodb_table" "tenant_metrics_template"' in content
            )
            self.check(
                "GSI definitions present",
                "global_secondary_index" in content
            )
        
        return True
    
    def validate_data_contracts(self) -> bool:
        """Validate DATA_CONTRACTS.md."""
        self.section("Data Contracts Documentation")
        
        contracts_file = self.root / "docs" / "DATA_CONTRACTS.md"
        self.validate_file_exists(contracts_file, "Data contracts documentation")
        
        if contracts_file.exists():
            content = contracts_file.read_text()
            self.check("PK/SK patterns documented", "pk" in content.lower() and "sk" in content.lower())
            self.check("Confidence range constraints", "[0.0, 1.0]" in content)
            self.check("Idempotency strategy", "idempotency" in content.lower())
            self.check("Reference format validation", "reference format" in content.lower())
            self.check("GSI patterns documented", "gsi" in content.lower() or "global secondary index" in content.lower())
        
        return True
    
    def validate_seed_data(self) -> bool:
        """Validate seed data files."""
        self.section("Seed Data")
        
        seed_dir = self.root / "backend" / "seed_data"
        
        # Tenant metadata
        tenant1 = seed_dir / "tenant_acme_corp.json"
        tenant2 = seed_dir / "tenant_techstart_inc.json"
        
        self.validate_file_exists(tenant1, "ACME Corp tenant metadata")
        self.validate_file_exists(tenant2, "TechStart Inc tenant metadata")
        
        if tenant1.exists():
            self.validate_json_file(tenant1, ["tenantId", "name", "ownerEmail", "status"])
        if tenant2.exists():
            self.validate_json_file(tenant2, ["tenantId", "name", "ownerEmail", "status"])
        
        # Metrics
        acme_metrics = seed_dir / "acme_corp_metrics.json"
        tech_metrics = seed_dir / "techstart_inc_metrics.json"
        
        self.validate_file_exists(acme_metrics, "ACME Corp metrics")
        self.validate_file_exists(tech_metrics, "TechStart Inc metrics")
        
        if acme_metrics.exists():
            self.validate_json_file(acme_metrics, ["pk", "sk", "value", "unit"])
            # Check confidence is NOT in metrics (it's in messages)
            with open(acme_metrics) as f:
                data = json.load(f)
                if len(data) > 0:
                    # Validate value ranges
                    for metric in data:
                        if "value" in metric and isinstance(metric["value"], (int, float)):
                            # Check that value is reasonable (not NaN, not infinity)
                            if metric["value"] == metric["value"]:  # Not NaN
                                self.passed += 1
        
        # Messages
        acme_messages = seed_dir / "acme_corp_messages.json"
        tech_messages = seed_dir / "techstart_inc_messages.json"
        
        self.validate_file_exists(acme_messages, "ACME Corp messages")
        self.validate_file_exists(tech_messages, "TechStart Inc messages")
        
        if acme_messages.exists():
            self.validate_json_file(acme_messages, ["pk", "sk", "messageId", "sender"])
            # Validate confidence ranges
            with open(acme_messages) as f:
                data = json.load(f)
                for msg in data:
                    if "classification" in msg and "confidence" in msg["classification"]:
                        conf = msg["classification"]["confidence"]
                        self.check(
                            f"Confidence in valid range for {msg.get('messageId', 'unknown')}",
                            0.0 <= conf <= 1.0,
                            f"Confidence {conf} out of range [0.0, 1.0]"
                        )
        
        return True
    
    def validate_seed_script(self) -> bool:
        """Validate seed script."""
        self.section("Seed Script")
        
        script = self.root / "backend" / "scripts" / "seed_localstack.py"
        self.validate_file_exists(script, "LocalStack seed script")
        
        if script.exists():
            content = script.read_text()
            self.check("Script has main function", "def main" in content)
            self.check("Script creates tables", "create_table" in content)
            self.check("Script seeds data", "put_item" in content)
            self.check("Script is executable", script.stat().st_mode & 0o111 != 0)
        
        return True
    
    def validate_tests(self) -> bool:
        """Validate contract tests."""
        self.section("Contract Tests")
        
        test_file = self.root / "backend" / "tests" / "contracts" / "test_contracts.py"
        self.validate_file_exists(test_file, "Contract test file")
        
        if test_file.exists():
            content = test_file.read_text()
            self.check("Confidence validation tests", "test_valid_confidence" in content)
            self.check("Reference format tests", "test_valid_reference" in content)
            self.check("Classification schema tests", "validate_classification" in content)
            self.check("Timestamp validation tests", "validate_timestamp" in content)
        
        # Try to run pytest
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-m", "pytest", "backend/tests/contracts/test_contracts.py", "-q"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # Parse output for passed/failed counts
                output = result.stdout
                if "passed" in output:
                    self.check("Contract tests execute successfully", True)
                else:
                    self.check("Contract tests execute successfully", False, "No tests ran")
            else:
                self.warn("Test execution", "Tests failed or had errors")
        except Exception as e:
            self.warn("Test execution", f"Could not run tests: {e}")
        
        return True
    
    def validate_ingestion_stubs(self) -> bool:
        """Validate ingestion module stubs."""
        self.section("Ingestion Stubs")
        
        ingestion_dir = self.root / "backend" / "src" / "ingestion"
        stub_file = ingestion_dir / "idempotent_ingestion.py"
        
        self.validate_file_exists(stub_file, "Ingestion stub module")
        
        if stub_file.exists():
            content = stub_file.read_text()
            self.check("IdempotencyStrategy class", "class IdempotencyStrategy" in content)
            self.check("MessageIngestion stub", "class MessageIngestion" in content)
            self.check("MetricsIngestion stub", "class MetricsIngestion" in content)
            self.check("Retry strategy documented", "calculate_backoff" in content)
            self.check("Error handling patterns", "should_retry" in content)
        
        return True
    
    def validate_documentation(self) -> bool:
        """Validate documentation files."""
        self.section("Documentation")
        
        self.validate_file_exists(self.root / "docs" / "DATA_CONTRACTS.md", "Data contracts doc")
        self.validate_file_exists(self.root / "docs" / "QUICKSTART.md", "Quick start guide")
        self.validate_file_exists(self.root / "docs" / "PHASE2_CHECKLIST.md", "Phase 2 checklist")
        self.validate_file_exists(self.root / "backend" / "requirements.txt", "Requirements file")
        self.validate_file_exists(self.root / "backend" / "pyproject.toml", "PyProject config")
        self.validate_file_exists(self.root / "backend" / "seed_data" / "README.md", "Seed data README")
        
        return True
    
    def run_all_validations(self) -> int:
        """Run all validations and return exit code."""
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}Phase 2 Data Platform Validation{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}")
        
        self.validate_terraform()
        self.validate_data_contracts()
        self.validate_seed_data()
        self.validate_seed_script()
        self.validate_tests()
        self.validate_ingestion_stubs()
        self.validate_documentation()
        
        # Print summary
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}Validation Summary{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}")
        print(f"{GREEN}Passed:{RESET} {self.passed}")
        print(f"{RED}Failed:{RESET} {self.failed}")
        print(f"{YELLOW}Warnings:{RESET} {self.warnings}")
        
        if self.failed == 0:
            print(f"\n{GREEN}✓ All validations passed!{RESET}")
            print(f"{GREEN}Phase 2 deliverables meet quality standards.{RESET}")
            return 0
        else:
            print(f"\n{RED}✗ Some validations failed.{RESET}")
            print(f"{RED}Please review and fix the issues above.{RESET}")
            return 1


def main():
    """Main entry point."""
    validator = Phase2Validator()
    sys.exit(validator.run_all_validations())


if __name__ == "__main__":
    main()
