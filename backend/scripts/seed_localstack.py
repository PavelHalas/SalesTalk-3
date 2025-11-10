#!/usr/bin/env python3
"""
SalesTalk LocalStack Seed Script

Seeds LocalStack DynamoDB with test tenants and sample data for local development.

Usage:
    python seed_localstack.py [--endpoint-url http://localhost:4566]

Requirements:
    - boto3
    - LocalStack running on localhost:4566 (default)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


# Configuration
DEFAULT_ENDPOINT_URL = "http://localhost:4566"
AWS_REGION = "us-east-1"
SEED_DATA_DIR = Path(__file__).parent.parent / "seed_data"


class LocalStackSeeder:
    """Seed LocalStack DynamoDB with test tenant data."""

    def __init__(self, endpoint_url: str = DEFAULT_ENDPOINT_URL):
        """Initialize seeder with DynamoDB client."""
        self.endpoint_url = endpoint_url
        self.dynamodb = boto3.client(
            "dynamodb",
            endpoint_url=endpoint_url,
            region_name=AWS_REGION,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        self.dynamodb_resource = boto3.resource(
            "dynamodb",
            endpoint_url=endpoint_url,
            region_name=AWS_REGION,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

    def create_tenants_metadata_table(self) -> None:
        """Create the global tenants-metadata table."""
        print("Creating tenants-metadata table...")
        
        try:
            self.dynamodb.create_table(
                TableName="tenants-metadata",
                KeySchema=[
                    {"AttributeName": "tenantId", "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "tenantId", "AttributeType": "S"},
                    {"AttributeName": "ownerEmail", "AttributeType": "S"},
                    {"AttributeName": "status", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "OwnerEmailIndex",
                        "KeySchema": [
                            {"AttributeName": "ownerEmail", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": "StatusIndex",
                        "KeySchema": [
                            {"AttributeName": "status", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            print("✓ Created tenants-metadata table")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print("✓ tenants-metadata table already exists")
            else:
                raise

    def create_tenant_messages_table(self, tenant_id: str) -> None:
        """Create a per-tenant messages table."""
        table_name = f"tenant-{tenant_id}-messages"
        print(f"Creating {table_name} table...")
        
        try:
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                    {"AttributeName": "sessionId", "AttributeType": "S"},
                    {"AttributeName": "timestamp", "AttributeType": "N"},
                    {"AttributeName": "sender", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "SessionIndex",
                        "KeySchema": [
                            {"AttributeName": "sessionId", "KeyType": "HASH"},
                            {"AttributeName": "timestamp", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": "SenderIndex",
                        "KeySchema": [
                            {"AttributeName": "sender", "KeyType": "HASH"},
                            {"AttributeName": "timestamp", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            print(f"✓ Created {table_name} table")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"✓ {table_name} table already exists")
            else:
                raise

    def create_tenant_metrics_table(self, tenant_id: str) -> None:
        """Create a per-tenant metrics table."""
        table_name = f"tenant-{tenant_id}-metrics"
        print(f"Creating {table_name} table...")
        
        try:
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                    {"AttributeName": "metricType", "AttributeType": "S"},
                    {"AttributeName": "timestamp", "AttributeType": "N"},
                    {"AttributeName": "dimensionKey", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "MetricTypeIndex",
                        "KeySchema": [
                            {"AttributeName": "metricType", "KeyType": "HASH"},
                            {"AttributeName": "timestamp", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": "DimensionIndex",
                        "KeySchema": [
                            {"AttributeName": "dimensionKey", "KeyType": "HASH"},
                            {"AttributeName": "timestamp", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            print(f"✓ Created {table_name} table")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"✓ {table_name} table already exists")
            else:
                raise

    def load_json_file(self, filepath: Path) -> Any:
        """Load JSON data from file."""
        with open(filepath, "r") as f:
            return json.load(f)

    def seed_tenant_metadata(self, tenant_data: Dict[str, Any]) -> None:
        """Seed a tenant into the tenants-metadata table."""
        table = self.dynamodb_resource.Table("tenants-metadata")
        tenant_id = tenant_data["tenantId"]
        
        print(f"Seeding tenant metadata for {tenant_id}...")
        try:
            # DynamoDB (boto3) requires Decimal instead of float for number types
            table.put_item(Item=self._convert_numbers(tenant_data))
            print(f"✓ Seeded tenant metadata for {tenant_id}")
        except Exception as e:
            print(f"✗ Error seeding tenant metadata: {e}")
            raise

    def seed_messages(self, tenant_id: str, messages: List[Dict[str, Any]]) -> None:
        """Seed messages for a tenant."""
        table_name = f"tenant-{tenant_id}-messages"
        table = self.dynamodb_resource.Table(table_name)
        
        print(f"Seeding {len(messages)} messages for {tenant_id}...")
        for message in messages:
            try:
                table.put_item(Item=self._convert_numbers(message))
            except Exception as e:
                print(f"✗ Error seeding message {message.get('messageId')}: {e}")
                raise
        print(f"✓ Seeded {len(messages)} messages for {tenant_id}")

    def seed_metrics(self, tenant_id: str, metrics: List[Dict[str, Any]]) -> None:
        """Seed metrics for a tenant."""
        table_name = f"tenant-{tenant_id}-metrics"
        table = self.dynamodb_resource.Table(table_name)
        
        print(f"Seeding {len(metrics)} metrics for {tenant_id}...")
        for metric in metrics:
            try:
                table.put_item(Item=self._convert_numbers(metric))
            except Exception as e:
                print(f"✗ Error seeding metric {metric.get('metricId')}: {e}")
                raise
        print(f"✓ Seeded {len(metrics)} metrics for {tenant_id}")

    def seed_tenant(
        self,
        tenant_file: Path,
        messages_file: Path,
        metrics_file: Path,
    ) -> None:
        """Seed a complete tenant with all data."""
        # Load data
        tenant_data = self.load_json_file(tenant_file)
        messages = self.load_json_file(messages_file)
        metrics = self.load_json_file(metrics_file)
        
        tenant_id = tenant_data["tenantId"]
        
        # Create tables
        self.create_tenant_messages_table(tenant_id)
        self.create_tenant_metrics_table(tenant_id)
        
        # Seed data
        self.seed_tenant_metadata(tenant_data)
        self.seed_messages(tenant_id, messages)
        self.seed_metrics(tenant_id, metrics)

    def seed_all(self) -> None:
        """Seed all test tenants."""
        print("=" * 60)
        print("SalesTalk LocalStack Seeder")
        print("=" * 60)
        print(f"Endpoint: {self.endpoint_url}")
        print(f"Region: {AWS_REGION}")
        print(f"Seed data directory: {SEED_DATA_DIR}")
        print("=" * 60)
        
        # Create global tables
        self.create_tenants_metadata_table()

        # Seed ACME Corporation
        print("\n--- Seeding ACME Corporation ---")
        self.seed_tenant(
            tenant_file=SEED_DATA_DIR / "tenant_acme_corp.json",
            messages_file=SEED_DATA_DIR / "acme_corp_messages.json",
            metrics_file=SEED_DATA_DIR / "acme_corp_metrics.json",
        )
        
        # Seed TechStart Inc
        print("\n--- Seeding TechStart Inc ---")
        self.seed_tenant(
            tenant_file=SEED_DATA_DIR / "tenant_techstart_inc.json",
            messages_file=SEED_DATA_DIR / "techstart_inc_messages.json",
            metrics_file=SEED_DATA_DIR / "techstart_inc_metrics.json",
        )
        
        print("\n" + "=" * 60)
        print("✓ Seeding complete!")
        print("=" * 60)
        print("\nSeeded tenants:")
        print("  1. acme-corp-001 (ACME Corporation)")
        print("  2. techstart-inc-002 (TechStart Inc)")
        print("\nTables created:")
        print("  - tenants-metadata")
        print("  - tenant-acme-corp-001-messages")
        print("  - tenant-acme-corp-001-metrics")
        print("  - tenant-techstart-inc-002-messages")
        print("  - tenant-techstart-inc-002-metrics")

    def _convert_numbers(self, obj: Any) -> Any:
        """Recursively convert float numbers to Decimal for DynamoDB compatibility."""
        if isinstance(obj, dict):
            return {k: self._convert_numbers(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert_numbers(v) for v in obj]
        if isinstance(obj, float):
            # Use Decimal(str(...)) to avoid binary float issues
            return Decimal(str(obj))
        return obj


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed LocalStack DynamoDB with test tenant data"
    )
    parser.add_argument(
        "--endpoint-url",
        default=DEFAULT_ENDPOINT_URL,
        help=f"LocalStack endpoint URL (default: {DEFAULT_ENDPOINT_URL})",
    )
    args = parser.parse_args()
    
    try:
        seeder = LocalStackSeeder(endpoint_url=args.endpoint_url)
        seeder.seed_all()
        return 0
    except Exception as e:
        print(f"\n✗ Seeding failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
