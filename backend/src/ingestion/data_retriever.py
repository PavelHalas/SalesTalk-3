import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr

class DataRetriever:
    """
    Retrieves data from DynamoDB based on classification results using a Query Registry.
    """
    
    def __init__(self, tenant_id: str, region_name: str = "us-east-1", endpoint_url: Optional[str] = None):
        self.tenant_id = tenant_id
        self.metrics_table_name = f"tenant-{tenant_id}-metrics"
        self.data_table_name = f"tenant-{tenant_id}-data"
        
        # Initialize DynamoDB resource
        self.dynamodb = boto3.resource(
            "dynamodb", 
            region_name=region_name,
            endpoint_url=endpoint_url
        )
        self.metrics_table = self.dynamodb.Table(self.metrics_table_name)
        self.data_table = self.dynamodb.Table(self.data_table_name)
        
        # Load Registry
        self.registry = self._load_registry()

    def _load_registry(self) -> List[Dict[str, Any]]:
        """Load the query registry from JSON file."""
        registry_path = Path(__file__).parent / "query_registry.json"
        try:
            with open(registry_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading query registry: {e}")
            return []

    def _find_matching_template(self, classification: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the best matching query template for the classification."""
        subject = classification.get("subject", {}).get("primary")
        intent = classification.get("intent", {}).get("primary")
        dimensions = classification.get("dimension", {})
        
        # Simple matching logic (can be enhanced with scoring)
        for template in self.registry:
            match = template.get("match", {})
            
            # Check Intent
            if intent not in match.get("intents", []):
                continue
                
            # Check Subject (singular/plural handling needed in real app)
            # For MVP, we assume exact match or simple singularization
            if subject not in match.get("subjects", []) and subject.rstrip('s') not in match.get("subjects", []):
                continue
                
            # Check Dimensions (Allowed/Supported)
            # Logic: 
            # 1. The query dimensions must be a SUBSET of the template's supported dimensions.
            #    (You can't ask for "Region" if the template doesn't support it)
            # 2. If the template lists "time", the query MUST have time.
            # 3. If the template lists other dimensions, the query MUST have at least one of them (unless only time is listed).
            
            supported_dims = match.get("dimensions", [])
            
            # Get query dimensions (keys only)
            query_dims = list(dimensions.keys())
            if classification.get("time"):
                query_dims.append("time")
                
            # Rule 1: No extra dimensions allowed
            # If query has "region" but template doesn't support it -> Skip
            extra_dims = [d for d in query_dims if d not in supported_dims]
            if extra_dims:
                continue
                
            # Rule 2: Time requirement
            if "time" in supported_dims and "time" not in query_dims:
                # Template supports time, but query doesn't have it.
                # Is it mandatory? In this simplified schema, we assume yes if it's the ONLY dimension.
                # But for "Ranking", time might be optional? 
                # Let's stick to: If "time" is in supported_dims, it is ALLOWED.
                # But we need a way to enforce "Required".
                # Heuristic: If the query has NO dimensions, and the template expects some, skip.
                pass

            # Rule 3: "Best Fit" / Specificity
            # We want to avoid "Point Lookup" matching "Ranking" just because it's a subset.
            # But "Point Lookup" has dimensions=["time"].
            # "Ranking" has dimensions=["time", "customer"...].
            # If query is ["time"], both match Rule 1.
            # We need to pick the one that is "tighter".
            # Actually, "Ranking" usually requires a grouping dimension.
            # If query is ["time"], it should NOT match "Ranking" (which needs a group).
            
            # Refined Logic:
            # If template has non-time dimensions, the query MUST have at least one of them.
            non_time_supported = [d for d in supported_dims if d != "time"]
            non_time_query = [d for d in query_dims if d != "time"]
            
            if non_time_supported and not non_time_query:
                # Template supports "customer", but query is just "time".
                # This template is likely a breakdown/ranking, not a point lookup.
                continue
            
            return template
            
        return None

    def _hydrate_template(self, template: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Replace placeholders in the template with actual values."""
        subject = classification.get("subject", {}).get("primary")
        time_data = classification.get("time", {})
        dimensions = classification.get("dimension", {})
        
        db_config = template["dynamodb"].copy()
        
        # Helper to safely get nested values
        def get_val(path):
            parts = path.split('.')
            if parts[0] == 'time':
                return time_data.get(parts[1], "")
            if parts[0] == 'dimension':
                dim_key = parts[1]
                # Handle dimension object structure {"value": "..."}
                dim_obj = dimensions.get(dim_key, {})
                if isinstance(dim_obj, dict):
                    return dim_obj.get("value", "")
                return dim_obj
            if parts[0] == 'subject':
                return subject
            if parts[0] == 'subject_singular':
                return subject.rstrip('s')
            if parts[0] == 'subject_upper':
                return subject.upper().rstrip('S')
            return ""

        # Replace placeholders in string values
        for key, value in db_config.items():
            if isinstance(value, str) and "{" in value:
                # Simple format replacement
                # Note: This is a basic implementation. A robust one would use regex.
                formatted_val = value
                import re
                placeholders = re.findall(r"\{(.*?)\}", value)
                for ph in placeholders:
                    replacement = get_val(ph)
                    formatted_val = formatted_val.replace(f"{{{ph}}}", str(replacement))
                db_config[key] = formatted_val
                
        return db_config

    def retrieve(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point to retrieve data based on classification.
        """
        # 1. Find Template
        template = self._find_matching_template(classification)
        if not template:
            return {
                "status": "error", 
                "message": "No matching query pattern found for this request."
            }
            
        # Check if implementation exists (PO mode support)
        if "dynamodb" not in template:
            return {
                "status": "not_implemented",
                "message": f"Capability '{template.get('id')}' is defined but has no database implementation yet."
            }

        # 2. Hydrate Template
        query_config = self._hydrate_template(template, classification)
        
        # 3. Select Table
        table_name = query_config.get("table", "metrics")
        table = self.data_table if table_name == "data" else self.metrics_table
        
        # 4. Build Query Args
        query_kwargs = {}
        
        # Handle Index
        if "index" in query_config:
            query_kwargs["IndexName"] = query_config["index"]
            
        # Handle KeyConditionExpression
        pk = query_config.get("pk")
        sk = query_config.get("sk")
        sk_prefix = query_config.get("sk_prefix")
        
        if pk:
            # Determine the actual key names based on table/index
            # This is a simplification. In reality, you'd map this from the schema.
            # For our schema:
            # Metrics Table: PK=pk, SK=sk
            # Data Table: PK=pk, SK=sk
            # Indices have different key names (e.g. metricType, timestamp)
            
            # HACK for MVP: We assume the template knows the key names or we use generic 'pk'/'sk'
            # A better way is to have the registry define the key attribute names too.
            # For now, let's assume standard PK/SK unless it's an index.
            
            pk_attr = "pk"
            sk_attr = "sk"
            
            if "index" in query_config:
                # Map index names to attribute names (Hardcoded for MVP based on schema)
                idx = query_config["index"]
                if idx == "MetricTypeIndex": pk_attr, sk_attr = "metricType", "timestamp"
                elif idx == "DimensionIndex": pk_attr, sk_attr = "dimensionKey", "timestamp"
                elif idx == "EntityTypeIndex": pk_attr, sk_attr = "entityType", "entityId"
                elif idx == "NameIndex": pk_attr, sk_attr = "entityType", "name"
                elif idx == "ParentIndex": pk_attr, sk_attr = "parentId", "sk"
            
            key_condition = Key(pk_attr).eq(pk)
            
            if sk:
                key_condition = key_condition & Key(sk_attr).eq(sk)
            elif sk_prefix:
                key_condition = key_condition & Key(sk_attr).begins_with(sk_prefix)
                
            query_kwargs["KeyConditionExpression"] = key_condition

        # Handle FilterExpression (Dynamic Dimensions)
        dimensions = classification.get("dimension", {})
        filter_expression = None
        
        if query_config.get("filter_strategy") == "expression" and dimensions:
             for dim_name, dim_info in dimensions.items():
                val = dim_info.get("value")
                if val and val != "all":
                    # Use Attr for safe path handling
                    condition = Attr(f"dimensions.{dim_name}").eq(val)
                    if filter_expression is None:
                        filter_expression = condition
                    else:
                        filter_expression = filter_expression & condition
        
        if filter_expression:
            query_kwargs["FilterExpression"] = filter_expression

        # 5. Execute
        try:
            query_type = query_config.get("query_type", "query")
            
            if query_type == "get_item":
                # get_item has different syntax
                response = table.get_item(Key={pk_attr: pk, sk_attr: sk})
                item = response.get("Item")
                items = [item] if item else []
            else:
                response = table.query(**query_kwargs)
                items = response.get("Items", [])
            
            # 6. Post-Processing
            post_process = query_config.get("post_process")
            if post_process == "sort_desc":
                # Sort by value descending
                # Assumes items have a 'value' field
                items.sort(key=lambda x: float(x.get("value", 0)), reverse=True)
            elif post_process == "sort_asc":
                items.sort(key=lambda x: float(x.get("value", 0)))

            return {
                "status": "success",
                "items": items,
                "count": len(items),
                "query_metadata": {
                    "template_id": template["id"],
                    "table": table_name
                }
            }
            
        except Exception as e:
            print(f"DynamoDB Query Error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
