import boto3
import json
import sys
from pathlib import Path
from decimal import Decimal
from botocore.exceptions import ClientError

# Add src to path
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))
from ingestion.data_retriever import DataRetriever

# Configuration
ENDPOINT_URL = "http://localhost:4566"
REGION = "us-east-1"
TENANT_ID = "test-tenant"

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def setup_data():
    """Seed data for demonstration."""
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    
    metrics_table_name = f"tenant-{TENANT_ID}-metrics"
    data_table_name = f"tenant-{TENANT_ID}-data"
    
    # Create/Get Metrics Table
    try:
        metrics_table = dynamodb.create_table(
            TableName=metrics_table_name,
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
                {"AttributeName": "metricType", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "N"},
                {"AttributeName": "dimensionKey", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {"IndexName": "MetricTypeIndex", "KeySchema": [{"AttributeName": "metricType", "KeyType": "HASH"}, {"AttributeName": "timestamp", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "DimensionIndex", "KeySchema": [{"AttributeName": "dimensionKey", "KeyType": "HASH"}, {"AttributeName": "timestamp", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}},
            ],
            BillingMode="PAY_PER_REQUEST"
        )
    except ClientError:
        metrics_table = dynamodb.Table(metrics_table_name)

    # Create/Get Data Table
    try:
        data_table = dynamodb.create_table(
            TableName=data_table_name,
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
                {"AttributeName": "entityType", "AttributeType": "S"},
                {"AttributeName": "name", "AttributeType": "S"},
                {"AttributeName": "parentId", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {"IndexName": "EntityTypeIndex", "KeySchema": [{"AttributeName": "entityType", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "NameIndex", "KeySchema": [{"AttributeName": "entityType", "KeyType": "HASH"}, {"AttributeName": "name", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "ParentIndex", "KeySchema": [{"AttributeName": "parentId", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
            ],
            BillingMode="PAY_PER_REQUEST"
        )
    except ClientError:
        data_table = dynamodb.Table(data_table_name)

    # Seed Data
    metrics_table.put_item(Item={"pk": "METRIC#revenue", "sk": "Q3", "value": 150000, "unit": "USD", "metricType": "revenue", "timestamp": 1696118400})
    metrics_table.put_item(Item={"pk": "METRIC#margin", "sk": "Q3", "value": Decimal("0.45"), "unit": "percent", "metricType": "margin", "timestamp": 1696118400})
    
    months = ["Jan", "Feb", "Mar"]
    for i, m in enumerate(months):
        metrics_table.put_item(Item={"pk": "METRIC#revenue", "sk": f"2025-{m}", "value": 10000 + (i * 1000), "metricType": "revenue", "timestamp": 1735689600 + (i * 2600000)})
        
    regions = ["EMEA", "NA", "APAC"]
    for r in regions:
        metrics_table.put_item(Item={"pk": "METRIC#revenue", "sk": f"Q3#{r}", "value": 50000, "dimensions": {"region": r}, "dimensionKey": r, "timestamp": 1696118400})

    metrics_table.put_item(Item={"pk": "METRIC#inventory_value", "sk": "AGING#30_days", "value": 10000, "age": "30_days"})
    
    # Seed Ranking Data (Top Entities)
    # Top Customers (Generic Score/Metric)
    for i in range(1, 6):
        metrics_table.put_item(Item={
            "pk": "METRIC#customers", 
            "sk": f"Q3#Cust{i}", 
            "value": i * 100, 
            "name": f"Customer {i}",
            "timestamp": 1696118400
        })

    # Seed Metric Ranking (Revenue by Customer)
    for i in range(1, 6):
        metrics_table.put_item(Item={
            "pk": "METRIC#revenue", 
            "sk": f"Q3#Cust{i}", 
            "value": i * 5000, 
            "dimensions": {"customer": f"Cust{i}"},
            "timestamp": 1696118400
        })

    data_table.put_item(Item={"pk": "CUSTOMER#123", "sk": "PROFILE", "name": "Acme Corp", "entityType": "customer", "segment": "Enterprise"})
    data_table.put_item(Item={"pk": "ORDER#999", "sk": "DETAILS", "parentId": "123", "amount": 5000, "entityType": "order"})

def run_scenarios():
    retriever = DataRetriever(tenant_id=TENANT_ID, endpoint_url=ENDPOINT_URL)
    
    scenarios = [
        ("Point Lookup", {"intent": {"primary": "what"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"period": "Q3"}, "dimension": {}}),
        ("Trend Analysis", {"intent": {"primary": "trend"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"year": "2025"}, "dimension": {}}),
        ("Dimensional Breakdown", {"intent": {"primary": "breakdown"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"period": "Q3"}, "dimension": {"breakdown_by": {"value": "region"}}}),
        ("Metric Ranking", {"intent": {"primary": "rank"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"period": "Q3"}, "dimension": {"limit": {"value": 5}, "direction": {"value": "top"}}}),
        ("Period Ranking", {"intent": {"primary": "rank"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"year": "2025"}, "dimension": {"window": {"value": "year"}}}),
        ("Inventory Aging", {"intent": {"primary": "list"}, "subject": {"primary": "inventory"}, "measure": {"primary": "inventory_value"}, "dimension": {"age": {"value": "30_days"}}}),
        ("Top Entities", {"intent": {"primary": "rank"}, "subject": {"primary": "customers"}, "time": {"period": "Q3"}, "dimension": {"limit": {"value": 10}}}),
        ("List Entities", {"intent": {"primary": "list"}, "subject": {"primary": "customers"}, "subject_singular": "customer", "dimension": {}}),
        ("Entity Profile", {"intent": {"primary": "profile"}, "subject": {"primary": "customer"}, "subject_upper": "CUSTOMER", "dimension": {"id": {"value": "123"}}}),
        ("Entity Search", {"intent": {"primary": "find"}, "subject": {"primary": "customer"}, "subject_singular": "customer", "dimension": {"name": {"value": "Acme Corp"}}}),
        ("Child Entities", {"intent": {"primary": "list"}, "subject": {"primary": "orders"}, "dimension": {"customer_id": {"value": "123"}}}),
        ("Anomaly Detection", {"intent": {"primary": "anomaly"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"year": "2025"}, "dimension": {}}),
        ("Target Tracking", {"intent": {"primary": "target"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"period": "Q3"}, "dimension": {}}),
        ("Correlation Analysis", {"intent": {"primary": "correlation"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"year": "2025"}, "dimension": {"related_metric": {"value": "marketing_spend"}}}),
    ]

    print(f"{'SCENARIO':<25} | {'STATUS':<10} | {'ITEMS':<5} | {'SAMPLE OUTPUT'}")
    print("-" * 100)

    for name, classification in scenarios:
        result = retriever.retrieve(classification)
        status = result.get("status", "unknown")
        items = result.get("items", [])
        count = len(items)
        
        # Format sample output
        sample = ""
        if count > 0:
            # Simplify item for display
            first_item = items[0]
            if "value" in first_item:
                sample = f"Value: {first_item['value']}"
            elif "name" in first_item:
                sample = f"Name: {first_item['name']}"
            elif "amount" in first_item:
                sample = f"Amount: {first_item['amount']}"
            else:
                sample = str(first_item)[:50] + "..."
        else:
            sample = "No data found"
            
        print(f"{name:<25} | {status:<10} | {count:<5} | {sample}")

if __name__ == "__main__":
    setup_data()
    run_scenarios()