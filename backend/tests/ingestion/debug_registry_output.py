import boto3
import json
import csv
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
CSV_PATH = Path(__file__).parents[1] / "data" / "product_owner_questions.csv"

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
    
    scenarios = []
    
import re

# ... (imports)

# ... (setup_data)

def run_scenarios():
    retriever = DataRetriever(tenant_id=TENANT_ID, endpoint_url=ENDPOINT_URL)
    
    scenarios = []
    
    # Load scenarios from CSV
    if CSV_PATH.exists():
        print(f"Loading scenarios from {CSV_PATH}...")
        with open(CSV_PATH, 'r') as f:
            lines = f.readlines()
            
        # Skip header
        for row_idx, line in enumerate(lines[1:]):
            line = line.strip()
            if not line: continue
            
            try:
                # Regex to split by comma, ignoring commas inside quotes
                # This handles nested quotes better than simple csv readers sometimes
                parts = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)
                
                row = []
                for p in parts:
                    p = p.strip()
                    if p.startswith('"') and p.endswith('"'):
                        p = p[1:-1]
                        p = p.replace('""', '"')
                    row.append(p)

                if len(row) < 5:
                    print(f"Skipping malformed row {row_idx+2}: {row}")
                    continue
                    
                # Map by index
                # question,intent,subject,measure,dimension,time
                question = row[0]
                intent = row[1]
                subject = row[2]
                measure = row[3]
                dimension_str = row[4]
                time_str = row[5] if len(row) > 5 else "{}"
                
                # Normalize dimensions
                normalized_dims = {}
                if dimension_str:
                    try:
                        raw_dims = json.loads(dimension_str)
                        for k, v in raw_dims.items():
                            if isinstance(v, dict) and "value" in v:
                                normalized_dims[k] = v
                            else:
                                normalized_dims[k] = {"value": v}
                    except json.JSONDecodeError:
                        raise

                classification = {
                    "intent": {"primary": intent},
                    "subject": {"primary": subject},
                    "measure": {"primary": measure},
                    "time": json.loads(time_str) if time_str else {},
                    "dimension": normalized_dims
                }
                scenarios.append((question, classification))
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON in row {row_idx+2}: {line} - {e}")
            except Exception as e:
                print(f"Error processing row {row_idx+2}: {line} - {e}")
    else:
        print(f"Warning: CSV file not found at {CSV_PATH}")
        # Fallback to hardcoded scenarios if CSV is missing
        scenarios = [
            ("Point Lookup", {"intent": {"primary": "what"}, "subject": {"primary": "revenue"}, "measure": {"primary": "revenue"}, "time": {"period": "Q3"}, "dimension": {}}),
            # ... (rest of the hardcoded scenarios could go here, but let's rely on CSV for now as requested)
        ]

    print(f"{'SCENARIO':<50} | {'STATUS':<10} | {'ITEMS':<5} | {'SAMPLE OUTPUT'}")
    print("-" * 120)

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
            
        # Truncate name if too long
        display_name = (name[:47] + '...') if len(name) > 47 else name
        print(f"{display_name:<50} | {status:<10} | {count:<5} | {sample}")

if __name__ == "__main__":
    setup_data()
    run_scenarios()