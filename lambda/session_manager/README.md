# Session Manager Lambda

The Session Manager is the core orchestration Lambda function that handles session lifecycle management and Bedrock Agent workflow execution using an asynchronous invocation pattern.

## Purpose

This Lambda function serves two critical roles:
1. **API Handler**: Responds to HTTP requests from API Gateway (session creation, status checks)
2. **Workflow Orchestrator**: Executes long-running Bedrock Agent workflows asynchronously

## Architecture

### Asynchronous Self-Invocation Pattern

The Session Manager uses Lambda self-invocation to handle long-running workflows:

```
POST /api/submit-assessment (API Gateway)
    ↓
SessionManager creates session (100-200ms)
    ↓
Returns: { session_id, status: "PENDING" }
    ↓
SessionManager invokes itself asynchronously
    ↓
Background workflow runs (3-5 minutes)
    ↓
Status updates written to DynamoDB
    ↓
Frontend polls /api/agent-status/{sessionId}
```

### Why Asynchronous?

- **API Gateway Timeout**: 29 seconds maximum
- **Agent Workflow Duration**: 3-5 minutes typical
- **Solution**: Return session ID immediately, process in background
- **Lambda Timeout**: 900 seconds (15 minutes) for async execution

## Functions

### `handler(event, context)`
Main entry point that routes between:
- **API Gateway requests**: HTTP events from client
- **Async workflow invocations**: Direct Lambda events with `action: 'PROCESS_AGENT_WORKFLOW'`

### `create_session(...)`
Creates a new session record in DynamoDB with `PENDING` status.

**Parameters:**
- `client_name`: Client organization name
- `project_name`: Project title
- `industry`: Industry sector
- `requirements`: Raw meeting notes/requirements
- `duration`: Desired project duration
- `team_size`: Number of team members

**Returns:** `session_id` (UUID)

### `invoke_agent_async(...)`
Invokes the Lambda function itself asynchronously to process the Bedrock Agent workflow.

**Pattern:**
```python
lambda_client.invoke(
    FunctionName=os.environ['AWS_LAMBDA_FUNCTION_NAME'],
    InvocationType='Event',  # Asynchronous
    Payload=json.dumps({
        'action': 'PROCESS_AGENT_WORKFLOW',
        'session_id': session_id,
        ...
    })
)
```

### `invoke_bedrock_agent(...)`
Executes the complete Bedrock Agent workflow with:
- **Retry logic**: 3 attempts with exponential backoff
- **Throttling handling**: Automatic rate limit detection
- **Event streaming**: Real-time progress updates to DynamoDB
- **Progress tracking**: 0-100% with stage indicators

**Workflow Steps:**
1. Analyze requirements (RequirementsAnalyzer)
2. Calculate costs (CostCalculator)
3. Retrieve templates (TemplateRetriever)
4. Generate PowerPoint (PowerPointGenerator)
5. Generate SOW (SOWGenerator)

### `update_session_status(...)`
Helper function to update session status in DynamoDB.

**Parameters:**
- `session_id`: Session identifier
- `status`: New status (PENDING, PROCESSING, COMPLETED, ERROR)
- `stage`: Current workflow stage (optional)
- `progress`: Completion percentage 0-100 (optional)
- `error_message`: Error details (optional)

### `get_session_status(session_id)`
Retrieves current session state from DynamoDB.

**Returns:**
```python
{
    'session_id': str,
    'status': str,
    'current_stage': str,
    'progress': int,
    'client_name': str,
    'project_name': str,
    'industry': str,
    'duration': str,
    'team_size': int,
    'requirements_data': dict,
    'cost_data': dict,
    'agent_events': str,  # JSON string
    'template_paths': list,
    'document_urls': list,
    'error_message': str,
    'created_at': str,
    'updated_at': str
}
```

## Event Types

### API Gateway Event (Synchronous)
```python
{
    'httpMethod': 'POST',
    'path': '/api/submit-assessment',
    'body': '{"client_name": "...", "requirements": "..."}'
}
```

### Async Workflow Event (Background)
```python
{
    'action': 'PROCESS_AGENT_WORKFLOW',
    'session_id': 'uuid',
    'client_name': 'Acme Corp',
    'project_name': 'E-commerce Platform',
    'industry': 'Retail',
    'requirements': 'Meeting notes...',
    'duration': '6 months',
    'team_size': 5
}
```

## API Endpoints

### POST `/api/submit-assessment`
Create a new assessment session and start workflow.

**Request:**
```json
{
  "client_name": "Acme Corp",
  "project_name": "E-commerce Platform",
  "industry": "Retail",
  "requirements": "Build a modern e-commerce platform...",
  "duration": "6 months",
  "team_size": 5
}
```

**Response (< 500ms):**
```json
{
  "session_id": "uuid",
  "status": "PENDING",
  "message": "Assessment request received. Processing in background.",
  "poll_url": "/api/agent-status/uuid"
}
```

### GET `/api/agent-status/{session_id}`
Get current session status and events.

**Response:**
```json
{
  "session_id": "uuid",
  "status": "PROCESSING",
  "current_stage": "Running CostCalculator",
  "progress": 50,
  "client_name": "Acme Corp",
  "agent_events": "[{...}]",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:32:15Z"
}
```

### GET `/api/results/{session_id}`
Get generated documents and cost data.

**Response:**
```json
{
  "powerpoint_url": "https://s3.../presentation.pptx",
  "sow_url": "https://s3.../sow.docx",
  "cost_data": {
    "total_cost": 150000,
    "total_hours": 1200,
    "complexity_level": "High"
  }
}
```

## Environment Variables

Required environment variables:

```bash
# DynamoDB Tables
SESSIONS_TABLE_NAME=scopesmith-sessions

# Bedrock Configuration
BEDROCK_AGENT_ID=ABCD1234EF
BEDROCK_AGENT_ALIAS_ID=TSTALIASID

# S3 Buckets
TEMPLATES_BUCKET_NAME=scopesmith-templates
ARTIFACTS_BUCKET_NAME=scopesmith-artifacts

# Lambda (auto-set)
AWS_LAMBDA_FUNCTION_NAME=ScopeSmithLambda-SessionManager
```

## Status Flow

```
PENDING (Session created)
    ↓
PROCESSING (Agent workflow started)
    ↓
ANALYZING_REQUIREMENTS (RequirementsAnalyzer running)
    ↓
REQUIREMENTS_ANALYZED (Analysis complete)
    ↓
CALCULATING_COSTS (CostCalculator running)
    ↓
COSTS_CALCULATED (Cost calculation complete)
    ↓
GENERATING_POWERPOINT (PowerPointGenerator running)
    ↓
POWERPOINT_GENERATED (Presentation complete)
    ↓
GENERATING_SOW (SOWGenerator running)
    ↓
COMPLETED (All documents generated)
    
OR

ERROR (Workflow failed)
CONFIGURATION_ERROR (Agent not configured)
```

## Progress Tracking

The function tracks progress through stages:

```python
stage_progress = {
    'RequirementsAnalyzer': 30,   # 30% complete
    'CostCalculator': 50,          # 50% complete
    'TemplateRetriever': 60,       # 60% complete
    'PowerPointGenerator': 80,     # 80% complete
    'SOWGenerator': 95             # 95% complete
}
```

## Agent Event Types

Events stored in DynamoDB `agent_events` field:

```python
{
    'type': 'reasoning',      # Agent thinking (ReAct pattern)
    'type': 'tool_call',      # Lambda function invocation
    'type': 'tool_response',  # Function result
    'type': 'chunk',          # Streaming text
    'type': 'warning',        # Throttling alert
    'type': 'final_response'  # Agent completion
}
```

## Error Handling

### Configuration Errors
```python
if agent_id == 'PLACEHOLDER_AGENT_ID':
    raise ValueError("Bedrock Agent placeholders detected. 
                     Please run setup-agentcore.py")
```

### Throttling Errors
```python
# Exponential backoff with 3 retries
for attempt in range(max_retries):
    try:
        response = bedrock_agent_runtime.invoke_agent(...)
        break
    except ClientError as e:
        if e.response['Error']['Code'] == 'ThrottlingException':
            wait_time = retry_delay * (2 ** attempt)
            time.sleep(wait_time)
```

### Rate Limiting (DynamoDB)
```python
# Batch updates to avoid throttling
if time.time() - last_update_time > update_interval:
    dynamodb.update_item(...)
    last_update_time = time.time()
```

## Dependencies

See `requirements.txt`:
```
boto3>=1.28.0
```

## Testing

### Test Synchronous Session Creation
```bash
python -c "
import json
from app import handler
event = {
    'httpMethod': 'POST',
    'path': '/api/submit-assessment',
    'body': json.dumps({
        'client_name': 'Test Client',
        'requirements': 'Test requirements'
    })
}
print(handler(event, None))
"
```

### Test Async Workflow
```bash
python -c "
from app import handler
event = {
    'action': 'PROCESS_AGENT_WORKFLOW',
    'session_id': 'test-session-id',
    'client_name': 'Test Client',
    'requirements': 'Test requirements'
}
print(handler(event, None))
"
```

## Deployment

Deployed via CDK LambdaStack with:
- **Timeout**: 900 seconds (15 minutes)
- **Memory**: 512 MB
- **IAM Permissions**:
  - DynamoDB read/write
  - Bedrock Agent invocation
  - S3 read/write
  - Lambda self-invocation (`lambda:InvokeFunction`)

## Logging

All logs use structured format with `[SESSION]` prefix:
```
[SESSION] Created session: uuid
[SESSION] Invoking async workflow for session: uuid
[BEDROCK AGENT] Starting invocation for session: uuid
[BEDROCK AGENT] ✓ Agent invoked successfully
[CHUNK #1] Agent response text...
[TOOL CALL #1] Action Group: RequirementsAnalyzer
```

## Performance

- **Session Creation**: 100-200ms
- **API Response**: < 500ms
- **Agent Workflow**: 3-5 minutes
- **Status Update**: < 100ms
- **DynamoDB Writes**: Rate-limited to 1/second per session

## Related Documentation

- [Main README](../../README.md) - Project overview
- [API Stack](../../cdk/stacks/api_stack.py) - API Gateway configuration
- [Lambda Stack](../../cdk/stacks/lambda_stack.py) - Lambda deployment
