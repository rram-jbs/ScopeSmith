# ScopeSmith

AI-powered proposal generation system using AWS Bedrock Agents with asynchronous workflow processing.

## Architecture Overview

ScopeSmith uses a serverless architecture on AWS with **asynchronous workflow execution** to prevent API Gateway timeouts and provide real-time status updates.

### Asynchronous Workflow Pattern

The system implements a modern async pattern:
1. **Immediate Response**: API returns session ID in <500ms
2. **Background Processing**: Lambda invokes itself asynchronously for long-running agent workflow
3. **Status Polling**: Frontend polls every 2 seconds for real-time updates
4. **No Timeouts**: API Gateway never waits for long-running operations

### Frontend
- **Framework**: Vue 3 + Vite
- **Styling**: Tailwind CSS with glassmorphic design
- **Hosting**: S3 + CloudFront
- **Key Features**:
  - Real-time agent orchestration viewer
  - 8-step workflow progress tracking with percentage (0-100)
  - Live event streaming from Bedrock Agent
  - Automatic status polling (2-second intervals)

### Backend Infrastructure
- **API Gateway**: REST API with CORS support (29-second timeout per endpoint)
- **Lambda Functions**: 
  - `SessionManager`: Handles session creation and async Bedrock Agent invocation (15-minute timeout)
  - `RequirementsAnalyzer`: Analyzes client requirements using Amazon Nova Pro
  - `CostCalculator`: Calculates project costs with AI validation
  - `TemplateRetriever`: Manages PowerPoint and SOW templates
  - `PowerPointGenerator`: Creates presentation documents with AI content generation
  - `SOWGenerator`: Generates Statement of Work documents with AI content generation
- **Bedrock Agent**: Orchestrates the workflow autonomously
- **DynamoDB**: Sessions and rate sheets storage with real-time status tracking
- **S3**: Template and artifact storage

## Asynchronous Architecture

### Session Manager Workflow
```
POST /api/submit-assessment
    ↓
SessionManager creates session (100-200ms)
    ↓
Returns: { session_id: "...", status: "PENDING" }
    ↓
SessionManager invokes itself asynchronously (Lambda Event invocation)
    ↓
Background workflow runs (3-5 minutes):
  PENDING → PROCESSING → COMPLETED
    ↓
Frontend polls /api/agent-status/{sessionId} every 2s
    ↓
Status updates include:
  - status: PENDING | PROCESSING | COMPLETED | ERROR
  - progress: 0-100 (percentage)
  - current_stage: "Running RequirementsAnalyzer"
  - agent_events: [tool calls, responses, reasoning]
```

### Lambda Self-Invocation Pattern
The SessionManager Lambda uses a self-invocation pattern:
- **Synchronous mode** (API Gateway): Creates session, returns immediately
- **Asynchronous mode** (Event invocation): Processes Bedrock Agent workflow
- **IAM permissions**: Lambda can invoke itself with `InvocationType='Event'`
- **Timeout allocation**: 
  - API response: <500ms
  - Agent workflow: Up to 15 minutes

## Frontend-Backend Synchronization

### API Endpoints (api_stack.py)
```python
POST /api/submit-assessment      # Returns session_id in <500ms
GET /api/agent-status/{id}       # Fast polling (2s intervals)
GET /api/results/{id}            # Fetch generated documents
POST /api/upload-template        # Template management
```

### Status Values (Synchronized)
```javascript
// Backend (Lambda): session_manager/app.py
PENDING              // Session created, workflow queued
PROCESSING           // Agent actively running
COMPLETED            // All documents generated
ERROR                // Workflow failed
CONFIGURATION_ERROR  // Agent not configured

// Frontend: utils/constants.js
export const STATUS = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
  CONFIGURATION_ERROR: 'CONFIGURATION_ERROR'
}
```

### Progress Tracking
The backend provides granular progress updates:
```javascript
{
  progress: 50,  // 0-100 percentage
  current_stage: "Running CostCalculator",
  stage_progress: {
    'RequirementsAnalyzer': 30,
    'CostCalculator': 50,
    'TemplateRetriever': 60,
    'PowerPointGenerator': 80,
    'SOWGenerator': 95
  }
}
```

### Event Types (agent_events in DynamoDB)
```javascript
// Synchronized between backend Lambda and frontend AgentStreamViewer
{
  type: 'reasoning',      // Agent's thought process (ReAct pattern)
  type: 'tool_call',      // Action group invocation with parameters
  type: 'tool_response',  // Lambda function response
  type: 'chunk',          // Streaming text from agent
  type: 'warning',        // Rate limiting or throttling
  type: 'final_response'  // Agent's final output
}
```

### Workflow Step Mapping (Lambda Function Names)
```javascript
// Frontend: utils/constants.js
export const WORKFLOW_STAGES = [
  { id: 2, name: 'Analyzing Requirements', key: 'RequirementsAnalyzer' },
  { id: 3, name: 'Calculating Costs', key: 'CostCalculator' },
  { id: 4, name: 'Selecting Templates', key: 'TemplateRetriever' },
  { id: 5, name: 'Generating PowerPoint', key: 'PowerPointGenerator' },
  { id: 6, name: 'Generating SOW', key: 'SOWGenerator' }
]

// Backend: session_manager/app.py
stage_progress = {
  'RequirementsAnalyzer': 30,   # Actual Lambda function name
  'CostCalculator': 50,
  'TemplateRetriever': 60,
  'PowerPointGenerator': 80,
  'SOWGenerator': 95
}
```

## Deployment

### Prerequisites
- AWS Account with appropriate permissions
- Amazon Bedrock access enabled (us-east-1 region)
- GitHub repository with OIDC configured
- GitHub Secrets configured:
  - `AWS_ACCOUNT_ID`
  - `AWS_ROLE_ARN`

### Infrastructure Deployment
The `deploy-infrastructure.yml` workflow handles:
1. CDK stack deployment (Infrastructure, Lambda, API, Frontend)
2. Lambda self-invocation IAM permissions
3. Bedrock model access (Amazon Nova Pro)
4. AgentCore Gateway setup via `setup-agentcore.py`
5. Rate sheets seeding
6. Sample template uploads

### CDK Configuration Updates
**Lambda Stack** (`cdk/stacks/lambda_stack.py`):
- Session Manager timeout: **900 seconds** (15 minutes for async workflow)
- API Gateway integration timeout: **29 seconds** (maximum allowed)
- Self-invocation IAM policy: `lambda:InvokeFunction` on own ARN
- Bedrock permissions: All document generators have `bedrock:InvokeModel`
- Environment variables: `BEDROCK_MODEL_ID=amazon.nova-pro-v1:0`

**API Stack** (`cdk/stacks/api_stack.py`):
- Integration timeout: 29 seconds (API Gateway maximum)
- CORS configuration: Wildcard origins for development
- No long-running operations on API Gateway

### Frontend Deployment
The `deploy-frontend.yml` workflow:
1. Builds Vue application with environment variables
2. Sets `VITE_API_BASE_URL` from CDK outputs
3. Syncs to S3 bucket
4. Invalidates CloudFront cache

### Manual Setup
If deploying manually:
```bash
# 1. Deploy infrastructure
cd cdk
cdk deploy --all

# 2. Configure Bedrock Agent
cd ../scripts
python setup-agentcore.py

# 3. Seed data
python seed-rate-sheets.py

# 4. Upload templates
python upload-sample-templates.py

# 5. Build and deploy frontend
cd ../frontend
npm install
VITE_API_BASE_URL=<api-gateway-url> npm run build
aws s3 sync dist/ s3://<frontend-bucket>/ --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
```

## Development

### Local Frontend Development
```bash
cd frontend
npm install

# Create .env.local with API Gateway URL
echo "VITE_API_BASE_URL=https://xxx.execute-api.us-east-1.amazonaws.com/prod" > .env.local

npm run dev
```

### Testing Lambda Functions Locally
```bash
cd lambda/session_manager

# Test synchronous session creation
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

# Test async workflow invocation
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

### Lambda Function Environment Variables
All Lambda functions expect:
- `SESSIONS_TABLE_NAME`: DynamoDB sessions table
- `BEDROCK_AGENT_ID`: Bedrock Agent ID (set by setup-agentcore.py)
- `BEDROCK_AGENT_ALIAS_ID`: Agent alias ID (set by setup-agentcore.py)
- `BEDROCK_MODEL_ID`: `amazon.nova-pro-v1:0` (for AI content generation)
- `TEMPLATES_BUCKET_NAME`: S3 bucket for templates
- `ARTIFACTS_BUCKET_NAME`: S3 bucket for generated documents
- `RATE_SHEETS_TABLE_NAME`: DynamoDB rate sheets table (CostCalculator only)
- `AWS_LAMBDA_FUNCTION_NAME`: Auto-set by Lambda (for self-invocation)

## Agent Configuration

The Bedrock Agent uses:
- **Foundation Model**: Amazon Nova Pro (50+ RPM, higher rate limits than Claude)
- **Action Groups**: 5 Lambda functions (RequirementsAnalyzer, CostCalculator, TemplateRetriever, PowerPointGenerator, SOWGenerator)
- **Session Management**: DynamoDB for state persistence with real-time updates
- **Throttling Handling**: Exponential backoff with retry logic (3 attempts, 2-8s delay)
- **Context Preservation**: Raw requirements + analyzed data passed to all models

## Monitoring

- **CloudWatch Logs**: All Lambda functions have structured logging with `[FUNCTION_NAME]` prefixes
- **CloudWatch Alarms**: Error rate alerts via SNS (threshold: 3 errors in 5 minutes)
- **Agent Traces**: Bedrock Agent traces enabled in CloudWatch
- **Frontend**: Real-time event streaming shows agent progress in UI
- **DynamoDB Updates**: Rate-limited to 1 update/second to avoid throttling

## Troubleshooting

### Agent Configuration Errors
If you see `CONFIGURATION_ERROR`:
1. Check that `setup-agentcore.py` ran successfully
2. Verify `BEDROCK_AGENT_ID` and `BEDROCK_AGENT_ALIAS_ID` are set in Lambda environment
3. Check Lambda function permissions for Bedrock in IAM console
4. Confirm Amazon Nova Pro model access in Bedrock console

### Frontend Not Receiving Events
1. Verify API Gateway CORS configuration allows your origin
2. Check `VITE_API_BASE_URL` environment variable in frontend build
3. Ensure DynamoDB `agent_events` field is stored as JSON string
4. Check browser console for polling errors (Network tab)

### Lambda Timeout Issues
If async workflow times out:
1. Check CloudWatch Logs for the async invocation (filter by session_id)
2. Verify Lambda timeout is set to 900 seconds (15 minutes)
3. Check for Bedrock API throttling errors in logs
4. Review DynamoDB write capacity (should have on-demand pricing)

### Status Not Updating
1. Check DynamoDB session record has `updated_at` field changing
2. Verify `progress` and `current_stage` fields are being written
3. Check frontend polling interval (should be 2 seconds)
4. Look for errors in browser console Network tab

### Cost Calculator JSON Parse Error
**Fixed in this update**: The cost calculator now properly:
- Initializes `bedrock` client before using it
- Parses nested JSON in `requirements_data` parameter
- Includes raw requirements in model prompts
- Handles Bedrock response parsing consistently

## Architecture Decisions

1. **Asynchronous Pattern**: Prevents API Gateway 29-second timeout by using Lambda self-invocation
2. **Amazon Nova Pro**: Chosen for higher rate limits (50+ RPM vs 10 RPM for Claude)
3. **Status Polling**: Frontend polls every 2 seconds instead of WebSockets (simpler, more reliable)
4. **Progress Tracking**: Numeric 0-100 progress with stage names for better UX
5. **Context Preservation**: Raw requirements passed to all AI models alongside analyzed data
6. **Bedrock Agent Gateway**: Uses action groups for ReAct orchestration pattern
7. **Event Streaming**: DynamoDB stores full event stream as JSON for frontend consumption
8. **Self-Invocation**: Lambda can invoke itself asynchronously for background processing
9. **Rate Limiting**: Batch DynamoDB updates (max 1/second) to avoid throttling
10. **GitHub Actions**: Automated deployment pipeline with environment-specific configs

## Features

- 🤖 AI-powered requirements analysis with Amazon Nova Pro
- 💰 Automated cost estimation with AI validation and recommendations
- 📊 Professional PowerPoint generation with AI content creation
- 📄 Detailed Statement of Work (SOW) with AI-generated sections
- 🎨 Modern, responsive UI with real-time status updates
- ⚡ Asynchronous workflow processing (no timeouts)
- 📈 Real-time progress tracking (0-100%)
- 🔄 Template management system
- 🔍 Complete audit trail with agent event logs

## Tech Stack

### Frontend
- Vue.js 3 with Composition API
- Vite build system
- Tailwind CSS for styling
- Axios for API communication
- Real-time status polling (2-second intervals)

### Backend
- Amazon Bedrock with Amazon Nova Pro
- AWS Lambda for serverless compute (with self-invocation)
- Amazon DynamoDB for state management
- Amazon S3 for document storage
- AWS API Gateway for REST endpoints (29s timeout)
- AWS CloudFront for content delivery
- IAM for Lambda self-invocation permissions

## Project Structure

```
scopesmith/
├── frontend/                      # Vue.js 3 Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── AgentStreamViewer.vue  # Real-time progress viewer
│   │   │   └── ...
│   │   ├── composables/
│   │   │   └── usePolling.js          # Status polling logic
│   │   └── utils/
│   │       └── constants.js           # Status constants (synced with backend)
├── cdk/                          # Infrastructure as Code
│   ├── stacks/
│   │   ├── lambda_stack.py           # 15-min timeout, self-invoke permissions
│   │   ├── api_stack.py              # 29s API Gateway timeout
│   │   └── ...
├── lambda/                       # Serverless Functions
│   ├── session_manager/
│   │   └── app.py                    # Async workflow pattern
│   ├── cost_calculator/
│   │   └── app.py                    # Fixed: Bedrock client + JSON parsing
│   └── ...
└── scripts/                      # Utility Scripts
    ├── setup-agentcore.py            # Bedrock Agent configuration
    └── ...
```

## CI/CD

The project uses GitHub Actions for continuous integration and deployment:

### Workflows

1. **Infrastructure Deployment** (`deploy-infrastructure.yml`)
   - Triggers: Push to `main` branch (cdk/**, lambda/**, scripts/** changes)
   - Actions:
     - Deploys CDK stacks with async configuration
     - Configures AgentCore with Amazon Nova Pro
     - Seeds sample data
     - Uploads templates
   - **New**: Includes Lambda self-invocation permissions

2. **Frontend Deployment** (`deploy-frontend.yml`)
   - Triggers: Push to `main` branch (frontend/** changes)
   - Actions:
     - Builds Vue.js application with `VITE_API_BASE_URL`
     - Deploys to S3
     - Invalidates CloudFront cache

3. **Lambda Testing** (`test-lambdas.yml`)
   - Triggers: Pull requests to `main` branch (lambda/** changes)
   - Actions:
     - Runs unit tests
     - Generates coverage reports

4. **Manual Infrastructure Destroy** (`manual-destroy.yml`)
   - Trigger: Manual workflow dispatch
   - Purpose: Safely tear down AWS infrastructure

### Environment Variables

The workflows use the following secrets:
- `AWS_ROLE_ARN`: IAM role for AWS authentication
- `AWS_ACCOUNT_ID`: AWS account identifier

## API Reference

### Assessment Submission
POST `/api/submit-assessment` (Returns in <500ms)
```json
Request:
{
  "client_name": "string",
  "project_name": "string",
  "industry": "string",
  "requirements": "string",
  "duration": "string",
  "team_size": 5
}

Response:
{
  "session_id": "uuid",
  "status": "PENDING",
  "message": "Assessment request received. Processing in background.",
  "poll_url": "/api/agent-status/{session_id}"
}
```

### Status Check (2-second polling)
GET `/api/agent-status/{session_id}`
```json
{
  "session_id": "uuid",
  "status": "PROCESSING",
  "current_stage": "Running CostCalculator",
  "progress": 50,
  "client_name": "string",
  "project_name": "string",
  "agent_events": "[{...}]",  // JSON string
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601"
}
```

### Results Retrieval
GET `/api/results/{session_id}`
```json
{
  "powerpoint_url": "https://s3.../presentation.pptx",
  "sow_url": "https://s3.../sow.docx",
  "cost_data": {
    "total_cost": 150000,
    "total_hours": 1200,
    "complexity_level": "High",
    "cost_breakdown": {...},
    "ai_insights": {...}
  }
}
```

## Security Features

- AWS IAM role-based access control
- Lambda self-invocation with least-privilege IAM policies
- API request validation
- CORS configuration (wildcard for development)
- Rate limiting via API Gateway (10 req/s, 20 burst)
- Data encryption at rest (DynamoDB, S3)
- Data encryption in transit (TLS 1.2+)
- Bedrock model access restricted by IAM

## Performance Characteristics

- **API Response Time**: <500ms (session creation only)
- **Agent Workflow**: 3-5 minutes (background processing)
- **Status Polling**: 2-second intervals
- **Lambda Timeout**: 15 minutes (async workflow)
- **API Gateway Timeout**: 29 seconds (sync requests)
- **DynamoDB Updates**: Rate-limited to 1/second per session
- **Bedrock Rate Limit**: 50+ RPM (Amazon Nova Pro)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure status constants match between frontend and backend
4. Commit changes with clear messages
5. Test async workflow locally
6. Open a pull request with detailed description

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built for AWS with asynchronous architecture best practices
- Powered by Amazon Bedrock and Amazon Nova Pro
- Frontend UI inspired by Apple's design system
- Async pattern based on AWS Lambda best practices