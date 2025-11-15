# 🚀 SalesTalk Lambda Functions

AWS Lambda handlers for conversational analytics with AI-powered classification and narrative generation.

---

## 📁 Directory Structure

```
lambda/
├── __init__.py
├── ai_adapter.py       # AI provider abstraction (Bedrock/Ollama)
├── classify.py         # Classification endpoint Lambda
└── chat.py             # Chat endpoint Lambda
```

---

## 🎯 Lambda Functions

### 1. Classification Lambda (`classify.py`)

**Purpose:** Classify user questions into structured components (intent, subject, measure, etc.)

**Handler:** `classify.lambda_handler`

**Input (API Gateway Event):**
```json
{
  "body": "{\"question\": \"What is Q3 revenue?\"}",
  "requestContext": {
    "requestId": "uuid",
    "authorizer": {
      "claims": {
        "custom:tenant_id": "acme-corp-001"
      }
    }
  }
}
```

**Output:**
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "X-Request-Id": "uuid"
  },
  "body": "{\"classification\": {...}, \"requestId\": \"uuid\", \"tenantId\": \"acme-corp-001\"}"
}
```

**Environment Variables:**
- `AI_PROVIDER`: `bedrock` (default) or `ollama`
- `BEDROCK_MODEL_ID`: Bedrock model identifier (default: `anthropic.claude-3-sonnet-20240229-v1:0`)
- `AWS_REGION`: AWS region (default: `us-east-1`)
- `OLLAMA_BASE_URL`: Ollama API URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL`: Ollama model name (default: `llama2`)
 - `USE_SELF_REPAIR`: `true|false` (default: `false`) — enable a tiny TRM-inspired recursive repair pass that fixes common misses (dimension cues like active/online, YTD window vs period, subject/measure family).
 - `SELF_REPAIR_STEPS`: integer (default: `1`) — max number of repair iterations.

**Features:**
- ✅ Tenant isolation via JWT claims
- ✅ Structured logging (tenant + requestId)
- ✅ Input validation (max 10,000 chars)
- ✅ Confidence range validation [0.0, 1.0]
- ✅ Error handling (400, 502, 500)
 - ✅ Optional TRM-inspired self-repair loop (off by default)

---

### 2. Chat Lambda (`chat.py`)

**Purpose:** Handle end-to-end chat interactions (classify → fetch data → generate narrative)

**Handler:** `chat.lambda_handler`

**Input (API Gateway Event):**
```json
{
  "body": "{\"message\": \"What is Q3 revenue?\", \"sessionId\": \"uuid\"}",
  "requestContext": {
    "requestId": "uuid",
    "authorizer": {
      "claims": {
        "custom:tenant_id": "acme-corp-001"
      }
    }
  }
}
```

**Output:**
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "X-Request-Id": "uuid",
    "X-Session-Id": "session-uuid"
  },
  "body": "{\"response\": \"...\", \"classification\": {...}, \"dataReferences\": [...]}"
}
```

**Environment Variables:** Same as Classification Lambda

**Features:**
- ✅ Complete chat flow (classify → data → narrative)
- ✅ Session management
- ✅ Data reference provenance
- ✅ Refusal handling (low confidence)
- ✅ Streaming scaffolding (for future WebSocket support)

---

## 🤖 AI Adapter Interface

**Module:** `ai_adapter.py`

**Purpose:** Abstract AI provider differences (Bedrock vs Ollama)

### Supported Providers

#### 1. AWS Bedrock (Production)

```python
from ai_adapter import BedrockAdapter

adapter = BedrockAdapter(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1"
)

classification = adapter.classify(
    question="What is Q3 revenue?",
    tenant_id="acme-corp-001",
    request_id="req-123"
)
```

**Requirements:**
- `boto3` library installed
- AWS credentials configured
- Bedrock model access enabled

#### 2. Ollama (Local Development)

```python
from ai_adapter import OllamaAdapter

adapter = OllamaAdapter(
    base_url="http://localhost:11434",
    model="llama2"
)

classification = adapter.classify(
    question="What is Q3 revenue?",
    tenant_id="acme-corp-001",
    request_id="req-123"
)
```

**Requirements:**
- `requests` library installed
- Ollama running locally or remotely

### Factory Function

```python
from ai_adapter import get_adapter, AIProvider

# Bedrock
adapter = get_adapter(AIProvider.BEDROCK, region="us-west-2")

# Ollama
adapter = get_adapter(AIProvider.OLLAMA, base_url="http://localhost:11434")
```

---

## 🔒 Security & Tenant Isolation

### Tenant ID Extraction

Both Lambdas extract `tenant_id` from JWT claims:

```python
tenant_id = event["requestContext"]["authorizer"]["claims"]["custom:tenant_id"]
```

**Supported claim names:**
- `custom:tenant_id` (preferred)
- `tenantId` (fallback)

### Validation

All inputs are validated:
- ✅ Tenant ID present in claims
- ✅ Request body not empty
- ✅ Question/message field present
- ✅ Length limits enforced (10,000 chars)
- ✅ Confidence values in [0.0, 1.0]

---

## 📊 Structured Logging

All operations log with context:

```json
{
  "level": "INFO",
  "message": "Classification completed successfully",
  "extra": {
    "tenant_id": "acme-corp-001",
    "request_id": "req-123",
    "latency_ms": 87,
    "confidence": 0.92,
    "intent": "what",
    "subject": "revenue"
  }
}
```

**Log Fields:**
- `tenant_id`: Tenant identifier (for filtering)
- `request_id`: Request correlation ID (for tracing)
- `latency_ms`: Request duration
- `confidence`: Classification confidence
- `intent`, `subject`, `measure`: Classification components

---

## 🧪 Testing

### Run Unit Tests

```bash
cd backend
pytest tests/lambda/ -v
```

### Run Integration Tests

```bash
pytest tests/integration/ -v -m integration
```

### Run with Coverage

```bash
pytest tests/lambda/ tests/integration/ --cov=lambda --cov-report=html
```

**Current Coverage:** 90% ✅
- `classify.py`: 100%
- `ai_adapter.py`: 90%
- `chat.py`: 82%

---

## 🚦 Error Handling

### HTTP Status Codes

| Code | Error Type | Description |
|------|-----------|-------------|
| **200** | Success | Request completed successfully |
| **400** | ValidationError | Invalid input (missing fields, invalid format) |
| **502** | AIProviderError | AI service temporarily unavailable |
| **500** | InternalServerError | Unexpected server error |

### Error Response Format

```json
{
  "error": "ValidationError",
  "message": "question field is required",
  "requestId": "req-123"
}
```

---

## 🔄 Streaming Response (Future)

The `chat.py` module includes streaming scaffolding for future WebSocket support:

```python
from chat import stream_chat_response

for event in stream_chat_response(message, tenant_id, session_id, request_id):
    # Send event to WebSocket client
    print(event)
```

**Event Types:**
- `classification_start`
- `classification_complete`
- `data_retrieval_start`
- `data_retrieval_complete`
- `narrative_start`
- `narrative_chunk`
- `complete`
- `error`

---

## 📦 Dependencies

### Production

```
boto3>=1.34.0          # AWS SDK (Bedrock)
requests>=2.31.0       # HTTP client (Ollama)
typing-extensions>=4.8.0
```

### Development/Testing

```
pytest>=7.4.0
pytest-cov>=4.1.0
```

---

## 🔧 Local Development

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run with Ollama (Local)

```bash
# Start Ollama
ollama serve

# Set environment
export AI_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama2

# Run tests
pytest tests/lambda/ -v
```

### 3. Run with LocalStack (Bedrock Simulation)

```bash
# Start LocalStack
docker-compose up -d localstack

# Set environment
export AI_PROVIDER=bedrock
export AWS_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566

# Run tests
pytest tests/lambda/ -v
```

---

## 📖 Integration with Evaluation Framework

Both Lambdas integrate with the evaluation framework (`backend/evaluation/`):

```python
from classify import lambda_handler as classify_handler

# Load gold dataset
with open("backend/evaluation/gold.json") as f:
    gold_data = json.load(f)

# Test classification
for question in gold_data["questions"]:
    event = {
        "body": json.dumps({"question": question["question"]}),
        "requestContext": {
            "requestId": "test-request",
            "authorizer": {
                "claims": {"custom:tenant_id": "test-tenant"}
            }
        }
    }
    
    response = classify_handler(event, None)
    # Compare with expected classification
```

---

## 🔗 Related Documentation

- [Data Contracts](../../docs/DATA_CONTRACTS.md) - Validation rules and schemas
- [Ontology](../ontology/ONTOLOGY_v0.md) - Classification taxonomy
- [Evaluation](../evaluation/README.md) - Test datasets and metrics
- [Architecture Overview](../../docs/architecture/ARCHITECTURE_OVERVIEW.md) - System design

---

## 🎯 Phase 5 Gate Criteria

✅ **All slice tests pass** (89 passed, 4 skipped)  
✅ **Coverage ≥80% new logic** (90% achieved)  
✅ **Classification Lambda implemented** with logging  
✅ **Chat endpoint implemented** with streaming scaffolding  
✅ **AI adapter interface** with Bedrock + Ollama support  
✅ **Integration tests** for end-to-end flow  

---

*Last updated: November 2025*
