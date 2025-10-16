# ScopeSmith

AI-powered proposal generation system using AWS Bedrock Agents with asynchronous workflow processing and real-time monitoring.

## Overview

ScopeSmith is a comprehensive AI-powered proposal generation system that creates professional project proposals, cost estimates, PowerPoint presentations, and Statements of Work (SOW) using Amazon Bedrock Agents. The system features a modern Vue.js 3 frontend with real-time agent workflow monitoring and an asynchronous serverless backend architecture.

## Architecture Overview

ScopeSmith uses a serverless architecture on AWS with **asynchronous workflow execution** to prevent API Gateway timeouts and provide real-time status updates.

### Asynchronous Workflow Pattern

The system implements a modern async pattern for handling long-running AI agent workflows:
1. **Immediate Response**: API returns session ID in <500ms
2. **Background Processing**: Lambda invokes itself asynchronously for long-running agent workflow
3. **Status Polling**: Frontend polls every 2 seconds for real-time updates
4. **Event Streaming**: Live agent events (reasoning, tool calls, responses) displayed in UI
5. **No Timeouts**: API Gateway never waits for long-running operations (3-5 minutes)

### System Components

#### Frontend (Vue.js 3 + Vite)
- **Framework**: Vue 3 with Composition API
- **Styling**: Tailwind CSS with glassmorphic design system
- **Hosting**: S3 + CloudFront CDN
- **Key Features**:
  - Real-time agent orchestration viewer with event streaming
  - 8-step workflow progress tracking with 0-100% completion
  - Live event streaming from Bedrock Agent (reasoning, tool calls, responses)
  - Automatic status polling (2-second intervals)
  - Color-coded event visualization with icons
  - Auto-scrolling to latest agent events
  - Three-stage workflow: Form → Processing → Results
  - Responsive design for desktop, tablet, and mobile

#### Backend Infrastructure
- **API Gateway**: REST API with CORS support (29-second timeout per endpoint)
- **Lambda Functions**: 
  - `SessionManager`: Handles session creation and async Bedrock Agent invocation (15-minute timeout)
  - `RequirementsAnalyzer`: Analyzes client requirements using Amazon Nova Pro
  - `CostCalculator`: Calculates project costs with AI validation
  - `TemplateRetriever`: Manages PowerPoint and SOW templates
  - `PowerPointGenerator`: Creates presentation documents with AI content generation
  - `SOWGenerator`: Generates Statement of Work documents with AI content generation
- **Bedrock Agent**: Orchestrates the workflow autonomously with ReAct pattern
- **DynamoDB**: Sessions and rate sheets storage with real-time status tracking
- **S3**: Template and artifact storage with presigned URLs
- **CloudWatch**: Structured logging and monitoring with alarms

## Asynchronous Architecture Deep Dive

### Session Manager Workflow
```
POST /api/submit-assessment
    ↓
SessionManager creates session in DynamoDB (100-200ms)
    ↓
Returns: { session_id: "...", status: "PENDING", poll_url: "..." }
    ↓
SessionManager invokes itself asynchronously (Lambda Event invocation)
    ↓
Background workflow runs (3-5 minutes):
  PENDING → PROCESSING (with real-time events) → COMPLETED
    ↓
Frontend polls GET /api/agent-status/{sessionId} every 2s
    ↓
Status updates include:
  - status: PENDING | PROCESSING | COMPLETED | ERROR | CONFIGURATION_ERROR
  - progress: 0-100 (percentage)
  - current_stage: "Running RequirementsAnalyzer"
  - agent_events: JSON array of [{type, timestamp, content}, ...]
    ↓
Final documents available via GET /api/results/{sessionId}
```

### Lambda Self-Invocation Pattern
The SessionManager Lambda uses a self-invocation pattern to handle long-running workflows:
- **Synchronous mode** (API Gateway): Creates session, returns immediately (<500ms)
- **Asynchronous mode** (Event invocation): Processes Bedrock Agent workflow (3-5 min)
- **IAM permissions**: Lambda can invoke itself with `InvocationType='Event'`
- **Timeout allocation**: 
  - API response: <500ms
  - Agent workflow: Up to 15 minutes (900 seconds)
- **Status tracking**: DynamoDB updated throughout workflow with rate limiting (1 update/sec)

## Frontend-Backend Synchronization

### API Endpoints (api_stack.py)
```python
POST /api/submit-assessment      # Returns session_id in <500ms
GET /api/agent-status/{id}       # Fast polling (2s intervals) with full event history
GET /api/results/{id}            # Fetch generated documents and cost data
POST /api/upload-template        # Template management (optional feature)
```

### Status Values (Synchronized)
```javascript
// Backend (Lambda): session_manager/app.py
PENDING              // Session created, workflow queued
PROCESSING           // Agent actively running, events streaming
COMPLETED            // All documents generated successfully
ERROR                // Workflow failed with error message
CONFIGURATION_ERROR  // Agent not configured (run setup-agentcore.py)

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
The backend provides granular progress updates based on workflow stages:
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
The AgentStreamViewer displays various event types from the Bedrock Agent:

| Event Type | Icon | Color | Description |
|------------|------|-------|-------------|
| `reasoning` | 🤔 | Blue | Agent's thought process (ReAct pattern) |
| `tool_call` | 🔧 | Green | Action group invocation with parameters |
| `tool_response` | ✅ | Yellow | Lambda function response data |
| `chunk` | 💬 | Purple | Streaming text from agent |
| `warning` | ⚠️ | Orange | Rate limiting or throttling |
| `error` | ❌ | Red | Error occurred during processing |
| `final_response` | 🎯 | Green | Agent's final output |

```javascript
// Event structure in DynamoDB (stored as JSON string)
{
  type: 'tool_call',
  timestamp: '2025-10-16T12:34:56.789Z',
  action_group: 'RequirementsAnalyzer',
  function: 'analyze_requirements',
  parameters: [...]
}
```

### Workflow Step Mapping (Lambda Function Names)
```javascript
// Frontend: utils/constants.js
export const WORKFLOW_STAGES = [
  { id: 1, name: 'Initializing', key: 'Initializing' },
  { id: 2, name: 'Analyzing Requirements', key: 'RequirementsAnalyzer' },
  { id: 3, name: 'Calculating Costs', key: 'CostCalculator' },
  { id: 4, name: 'Selecting Templates', key: 'TemplateRetriever' },
  { id: 5, name: 'Generating PowerPoint', key: 'PowerPointGenerator' },
  { id: 6, name: 'Generating SOW', key: 'SOWGenerator' },
  { id: 7, name: 'Finalizing', key: 'Finalizing' },
  { id: 8, name: 'Complete', key: 'Complete' }
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
- Amazon Nova Pro model access enabled in Bedrock console
- GitHub repository with OIDC configured for AWS authentication
- GitHub Secrets configured:
  - `AWS_ACCOUNT_ID`: Your AWS account ID
  - `AWS_ROLE_ARN`: IAM role ARN for GitHub Actions

### Infrastructure Deployment (Automated via GitHub Actions)
The `deploy-infrastructure.yml` workflow handles:
1. CDK stack deployment (Infrastructure, Lambda, API, Frontend stacks)
2. Lambda self-invocation IAM permissions configuration
3. Bedrock model access (Amazon Nova Pro) setup
4. AgentCore Gateway setup via `setup-agentcore.py`
5. Rate sheets seeding to DynamoDB
6. Sample template uploads to S3

### CDK Configuration Details

**Lambda Stack** (`cdk/stacks/lambda_stack.py`):
- Session Manager timeout: **900 seconds** (15 minutes for async workflow)
- API Gateway integration timeout: **29 seconds** (maximum allowed)
- Self-invocation IAM policy: `lambda:InvokeFunction` on own ARN (wildcard pattern)
- Bedrock permissions: All document generators have `bedrock:InvokeModel`
- Environment variables: `BEDROCK_MODEL_ID=amazon.nova-pro-v1:0`
- Memory allocations:
  - SessionManager: 256 MB
  - RequirementsAnalyzer: 512 MB
  - CostCalculator: 256 MB
  - TemplateRetriever: 256 MB
  - PowerPointGenerator: 1024 MB
  - SOWGenerator: 1024 MB

**API Stack** (`cdk/stacks/api_stack.py`):
- Integration timeout: 29 seconds (API Gateway maximum)
- CORS configuration: Wildcard origins for development (`*`)
- Rate limiting: 10 requests/second, 20 burst
- No long-running operations on API Gateway (all async)

**Frontend Stack** (`cdk/stacks/frontend_stack.py`):
- S3 bucket with static website hosting
- CloudFront distribution for global CDN
- Environment variable injection: `VITE_API_BASE_URL`

### Frontend Deployment (Automated via GitHub Actions)
The `deploy-frontend.yml` workflow:
1. Builds Vue application with environment variables
2. Sets `VITE_API_BASE_URL` from CDK outputs dynamically
3. Syncs built assets to S3 bucket
4. Invalidates CloudFront cache for immediate updates

### Manual Deployment Steps
If deploying manually (not recommended, use GitHub Actions):
```bash
# 1. Deploy infrastructure stacks
cd cdk
pip install -r requirements.txt
cdk bootstrap  # First time only
cdk deploy --all --require-approval never

# 2. Configure Bedrock Agent (creates agent, action groups, aliases)
cd ../scripts
pip install -r requirements.txt
python setup-agentcore.py

# 3. Seed rate sheets data
python seed-rate-sheets.py

# 4. Upload sample templates
python upload-sample-templates.py

# 5. Build and deploy frontend
cd ../frontend
npm install

# Get API Gateway URL from CDK outputs
API_URL=$(aws cloudformation describe-stacks --stack-name ScopeSmithApi --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)

# Build with API URL
VITE_API_BASE_URL=$API_URL npm run build

# Deploy to S3
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name ScopeSmithFrontend --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete

# Invalidate CloudFront cache
DIST_ID=$(aws cloudformation describe-stacks --stack-name ScopeSmithFrontend --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' --output text)
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

## Development

### Local Frontend Development
```bash
cd frontend
npm install

# Create .env.local with your deployed API Gateway URL
echo "VITE_API_BASE_URL=https://xxx.execute-api.us-east-1.amazonaws.com/prod" > .env.local

# Optional: Enable template upload feature
echo "VITE_ENABLE_TEMPLATE_UPLOAD=true" >> .env.local

# Start development server
npm run dev
# Visit http://localhost:5173
```

### Testing Lambda Functions Locally
```bash
cd lambda/session_manager

# Test synchronous session creation (API Gateway request)
python -c "
import json
from app import handler
event = {
    'httpMethod': 'POST',
    'path': '/api/submit-assessment',
    'body': json.dumps({
        'client_name': 'Test Client',
        'project_name': 'Test Project',
        'industry': 'Technology',
        'requirements': 'Build a web application with user authentication',
        'duration': '3 months',
        'team_size': 3
    })
}
result = handler(event, None)
print(json.dumps(json.loads(result['body']), indent=2))
"

# Test async workflow invocation (background processing)
python -c "
from app import handler
event = {
    'action': 'PROCESS_AGENT_WORKFLOW',
    'session_id': 'test-session-id',
    'client_name': 'Test Client',
    'project_name': 'Test Project',
    'industry': 'Technology',
    'requirements': 'Test requirements',
    'duration': '3 months',
    'team_size': 3
}
print(handler(event, None))
"
```

### Lambda Function Environment Variables
All Lambda functions expect the following environment variables (set automatically by CDK):
- `SESSIONS_TABLE_NAME`: DynamoDB sessions table name
- `BEDROCK_AGENT_ID`: Bedrock Agent ID (set by setup-agentcore.py)
- `BEDROCK_AGENT_ALIAS_ID`: Agent alias ID (set by setup-agentcore.py)
- `BEDROCK_MODEL_ID`: `amazon.nova-pro-v1:0` (for AI content generation)
- `TEMPLATES_BUCKET_NAME`: S3 bucket for templates
- `ARTIFACTS_BUCKET_NAME`: S3 bucket for generated documents
- `RATE_SHEETS_TABLE_NAME`: DynamoDB rate sheets table (CostCalculator only)
- `AWS_LAMBDA_FUNCTION_NAME`: Auto-set by Lambda runtime (for self-invocation)

## Agent Configuration

The Bedrock Agent uses:
- **Foundation Model**: Amazon Nova Pro (`amazon.nova-pro-v1:0`)
  - 50+ RPM rate limits (vs. 10 RPM for Claude)
  - Cost-effective for high-volume processing
  - Strong reasoning and tool-use capabilities
- **Action Groups**: 5 Lambda functions as tools
  - RequirementsAnalyzer: Analyzes and structures client requirements
  - CostCalculator: AI-powered cost estimation with validation
  - TemplateRetriever: Fetches appropriate templates from S3
  - PowerPointGenerator: Creates presentations with AI content
  - SOWGenerator: Generates detailed SOW documents
- **Session Management**: DynamoDB for state persistence with real-time updates
- **Throttling Handling**: Exponential backoff with retry logic (3 attempts, 2-8s delay)
- **Context Preservation**: Raw requirements + analyzed data passed to all models
- **ReAct Pattern**: Reasoning and Acting in a loop for autonomous workflow execution

## Monitoring & Observability

### CloudWatch Logs
- **Structured Logging**: All Lambda functions use `[FUNCTION_NAME]` prefixes
- **Log Groups**: Automatically created per Lambda function
- **Log Retention**: 7 days (configurable in CDK)
- **Search Patterns**:
  - `[SESSION]` - Session lifecycle events
  - `[BEDROCK AGENT]` - Agent invocation and event processing
  - `[TOOL CALL]` - Action group invocations
  - `[CHUNK]` - Streaming text chunks
  - `[ERROR]` - Error conditions

### CloudWatch Alarms
- **Error Rate**: Alerts via SNS when > 3 errors in 5 minutes
- **Throttling**: Monitors Lambda throttling events
- **Duration**: Alerts on functions approaching timeout

### Agent Traces
- **Bedrock Agent Traces**: Enabled in CloudWatch for debugging
- **Event Stream**: Full event history stored in DynamoDB `agent_events` field
- **Frontend Visibility**: Real-time event streaming in AgentStreamViewer component

### DynamoDB Metrics
- **Read/Write Capacity**: On-demand pricing mode (auto-scaling)
- **Update Throttling**: Rate-limited to 1 update/second per session
- **TTL**: Optional time-to-live for session cleanup

## Troubleshooting

### Agent Configuration Errors
**Symptom**: Status shows `CONFIGURATION_ERROR`

**Solutions**:
1. Verify `setup-agentcore.py` ran successfully:
   ```bash
   cd scripts
   python setup-agentcore.py
   ```
2. Check Lambda environment variables:
   ```bash
   aws lambda get-function-configuration --function-name ScopeSmith-SessionManager \
     --query 'Environment.Variables' --output json
   ```
3. Verify `BEDROCK_AGENT_ID` and `BEDROCK_AGENT_ALIAS_ID` are not placeholders
4. Confirm Amazon Nova Pro model access in Bedrock console (us-east-1)

### Frontend Not Receiving Events
**Symptom**: No events showing in AgentStreamViewer

**Solutions**:
1. Check API Gateway CORS configuration allows your origin
2. Verify `VITE_API_BASE_URL` in frontend `.env.local` or build environment
3. Ensure DynamoDB `agent_events` field is stored as JSON string
4. Check browser console Network tab for polling errors
5. Verify session_id in URL matches DynamoDB record

### Frontend Not Updating
**Symptom**: Status stays stuck on "PENDING" or "PROCESSING"

**Solutions**:
1. Check browser console for polling errors
2. Verify API Gateway endpoint is accessible (test with curl)
3. Check CloudWatch Logs for SessionManager errors
4. Verify DynamoDB session record has `updated_at` field changing
5. Test polling endpoint directly:
   ```bash
   curl https://xxx.execute-api.us-east-1.amazonaws.com/prod/api/agent-status/{session_id}
   ```

### Lambda Timeout Issues
**Symptom**: Async workflow times out before completing

**Solutions**:
1. Check CloudWatch Logs for the async invocation (filter by session_id)
2. Verify Lambda timeout is set to 900 seconds (15 minutes) in CDK
3. Check for Bedrock API throttling errors in logs
4. Review DynamoDB write capacity (should have on-demand pricing)
5. Look for network timeouts in Bedrock Agent invocation

### Status Not Updating
**Symptom**: Progress percentage stuck or not changing

**Solutions**:
1. Check DynamoDB session record has `updated_at` timestamp changing
2. Verify `progress` and `current_stage` fields are being written
3. Check frontend polling interval (should be 2 seconds in `usePolling.js`)
4. Look for errors in browser console Network tab
5. Verify DynamoDB update throttling (max 1/second per session)

### API Gateway Errors
**Symptom**: 502 Bad Gateway or 504 Gateway Timeout

**Solutions**:
1. Verify Lambda function is returning proper response format with CORS headers
2. Check Lambda execution role has necessary permissions
3. Review Lambda CloudWatch Logs for errors
4. Ensure async invocation happens before 29-second API timeout
5. Test Lambda function directly via AWS Console

### Document Generation Fails
**Symptom**: Workflow completes but no documents generated

**Solutions**:
1. Check PowerPointGenerator and SOWGenerator CloudWatch Logs
2. Verify templates exist in S3 templates bucket
3. Check Bedrock model permissions for content generation
4. Ensure artifacts bucket is writable by Lambda functions
5. Review `document_urls` field in DynamoDB session record

### Cost Calculator JSON Parse Error
**Fixed in latest version**. If you see JSON parsing errors:
1. Ensure `bedrock` client is initialized before use
2. Verify `requirements_data` parameter is parsed as nested JSON
3. Check that raw requirements are included in model prompts
4. Validate Bedrock response parsing handles nested JSON correctly

## Architecture Decisions & Rationale

1. **Asynchronous Pattern**: Prevents API Gateway 29-second timeout by using Lambda self-invocation, allowing 15-minute workflows
2. **Amazon Nova Pro**: Chosen for higher rate limits (50+ RPM vs 10 RPM for Claude) and cost-effectiveness
3. **Status Polling**: Frontend polls every 2 seconds instead of WebSockets (simpler, more reliable, no connection management)
4. **Progress Tracking**: Numeric 0-100 progress with stage names provides better UX than binary states
5. **Context Preservation**: Raw requirements passed to all AI models alongside analyzed data for consistency
6. **Bedrock Agent Gateway**: Uses action groups for ReAct orchestration pattern (autonomous decision-making)
7. **Event Streaming**: DynamoDB stores full event stream as JSON for frontend consumption and debugging
8. **Self-Invocation**: Lambda invokes itself asynchronously for background processing (no SQS/Step Functions needed)
9. **Rate Limiting**: Batch DynamoDB updates (max 1/second) to avoid throttling and reduce costs
10. **GitHub Actions**: Automated deployment pipeline with environment-specific configs eliminates manual errors
11. **CloudFront CDN**: Global content delivery for fast frontend load times
12. **On-Demand DynamoDB**: Auto-scaling capacity avoids provisioning complexity

## Features

### Core Capabilities
- 🤖 **AI-Powered Analysis**: Requirements analysis with Amazon Nova Pro
- 💰 **Automated Cost Estimation**: AI validation and recommendations with rate sheet integration
- 📊 **Professional Presentations**: PowerPoint generation with AI content creation
- 📄 **Detailed SOW**: Statement of Work with AI-generated sections
- 🎨 **Modern UI**: Glassmorphic design with real-time status updates
- ⚡ **Asynchronous Processing**: No timeouts, handles 3-5 minute workflows

### Real-Time Monitoring
- 📈 **Progress Tracking**: 0-100% completion with 8-step workflow visualization
- 🔄 **Event Streaming**: Live agent reasoning, tool calls, and responses
- 🎯 **Stage Indicators**: Visual workflow stage tracking with color coding
- 🔍 **Complete Audit Trail**: Full agent event logs stored and displayed

### Developer Experience
- 🚀 **Automated Deployment**: GitHub Actions for CI/CD
- 📦 **Template Management**: Upload and manage custom templates
- 🔒 **Security**: IAM role-based access control with least privilege
- 📊 **Monitoring**: CloudWatch Logs, alarms, and Bedrock traces
- 🧪 **Testing**: Local Lambda testing support

## Tech Stack

### Frontend
- **Vue.js 3** with Composition API and `<script setup>`
- **Vite** for fast build system and hot module replacement
- **Tailwind CSS** for utility-first styling
- **Axios** for HTTP requests with interceptors
- **Vue Router** for client-side routing
- **Real-time Polling** via composables (2-second intervals)
- **PostCSS** for CSS processing

### Backend
- **Amazon Bedrock** with Amazon Nova Pro foundation model
- **AWS Lambda** for serverless compute (with self-invocation pattern)
- **Amazon DynamoDB** for state management (on-demand capacity)
- **Amazon S3** for document storage (templates and artifacts)
- **AWS API Gateway** for REST endpoints (29s timeout)
- **AWS CloudFront** for content delivery network
- **IAM** for Lambda self-invocation permissions
- **CloudWatch** for logging, monitoring, and alarms

### DevOps
- **AWS CDK** (Python) for infrastructure as code
- **GitHub Actions** for CI/CD pipelines
- **AWS OIDC** for secure GitHub-to-AWS authentication

## Project Structure

```
scopesmith/
├── frontend/                           # Vue.js 3 Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── AgentStreamViewer.vue  # Real-time progress viewer
│   │   │   ├── AgentStatus.vue        # Status badge component
│   │   │   ├── AppHeader.vue          # Application header
│   │   │   ├── AssessmentForm.vue     # Project intake form
│   │   │   ├── ErrorMessage.vue       # Error display
│   │   │   ├── LoadingSpinner.vue     # Loading animation
│   │   │   └── ResultsDisplay.vue     # Documents and cost display
│   │   ├── composables/
│   │   │   ├── useApi.js              # API client wrapper
│   │   │   └── usePolling.js          # Status polling logic
│   │   ├── utils/
│   │   │   └── constants.js           # Status constants (synced with backend)
│   │   ├── views/
│   │   │   └── AssessmentView.vue     # Main assessment workflow view
│   │   ├── router/
│   │   │   └── index.js               # Vue Router configuration
│   │   ├── App.vue                    # Root component
│   │   └── main.js                    # Application entry point
│   ├── public/                        # Static assets
│   ├── index.html                     # HTML template
│   ├── package.json                   # Dependencies
│   ├── vite.config.js                 # Vite configuration
│   ├── tailwind.config.js             # Tailwind CSS configuration
│   └── README.md                      # Frontend documentation
├── cdk/                               # Infrastructure as Code
│   ├── stacks/
│   │   ├── infrastructure_stack.py   # DynamoDB, S3 buckets
│   │   ├── lambda_stack.py           # Lambda functions (15-min timeout)
│   │   ├── api_stack.py              # API Gateway (29s timeout)
│   │   └── frontend_stack.py         # S3 + CloudFront
│   ├── app.py                        # CDK app entry point
│   ├── cdk.json                      # CDK configuration
│   └── requirements.txt              # Python dependencies
├── lambda/                           # Serverless Functions
│   ├── session_manager/
│   │   ├── app.py                    # Async workflow pattern
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── requirements_analyzer/
│   │   ├── app.py                    # Amazon Nova Pro analysis
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── cost_calculator/
│   │   ├── app.py                    # AI-powered cost estimation
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── template_retriever/
│   │   ├── app.py                    # Template management
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── powerpoint_generator/
│   │   ├── app.py                    # PPT generation with AI
│   │   ├── requirements.txt
│   │   └── README.md
│   └── sow_generator/
│       ├── app.py                    # SOW generation with AI
│       ├── requirements.txt
│       └── README.md
├── scripts/                          # Utility Scripts
│   ├── setup-agentcore.py           # Bedrock Agent configuration
│   ├── seed-rate-sheets.py          # DynamoDB data seeding
│   ├── upload-sample-templates.py   # Template uploads
│   ├── validate-infrastructure.py   # Infrastructure validation
│   ├── requirements.txt
│   └── README.md
├── .github/
│   └── workflows/
│       ├── deploy-infrastructure.yml  # Backend deployment
│       ├── deploy-frontend.yml        # Frontend deployment
│       ├── test-lambdas.yml          # Lambda testing
│       └── manual-destroy.yml        # Infrastructure cleanup
├── LICENSE                           # MIT License
└── README.md                         # This file
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

### Workflows

1. **Infrastructure Deployment** (`deploy-infrastructure.yml`)
   - **Triggers**: Push to `main` branch with changes to `cdk/**`, `lambda/**`, or `scripts/**`
   - **Actions**:
     - Authenticates to AWS via OIDC
     - Deploys CDK stacks with async configuration
     - Configures AgentCore with Amazon Nova Pro
     - Seeds sample data to DynamoDB
     - Uploads templates to S3
   - **Includes**: Lambda self-invocation permissions and Bedrock agent setup

2. **Frontend Deployment** (`deploy-frontend.yml`)
   - **Triggers**: Push to `main` branch with changes to `frontend/**`
   - **Actions**:
     - Builds Vue.js application with `VITE_API_BASE_URL` from CDK outputs
     - Deploys to S3 bucket
     - Invalidates CloudFront cache for immediate updates
   - **Environment**: Production build with minification and optimization

3. **Lambda Testing** (`test-lambdas.yml`)
   - **Triggers**: Pull requests to `main` branch with changes to `lambda/**`
   - **Actions**:
     - Runs unit tests for all Lambda functions
     - Generates coverage reports
     - Lints Python code

4. **Manual Infrastructure Destroy** (`manual-destroy.yml`)
   - **Trigger**: Manual workflow dispatch via GitHub UI
   - **Purpose**: Safely tear down AWS infrastructure
   - **Safety**: Requires manual confirmation

### Environment Variables

The workflows use the following GitHub secrets:
- `AWS_ROLE_ARN`: IAM role ARN for AWS authentication via OIDC
- `AWS_ACCOUNT_ID`: AWS account identifier for resource ARNs

## API Reference

### Assessment Submission
**Endpoint**: `POST /api/submit-assessment`  
**Response Time**: < 500ms  
**Description**: Creates a session and starts async workflow processing

```json
Request:
{
  "client_name": "Acme Corporation",
  "project_name": "E-commerce Platform Modernization",
  "industry": "Retail",
  "requirements": "Detailed project requirements and meeting notes...",
  "duration": "6 months",
  "team_size": 5
}

Response:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "message": "Assessment request received. Processing in background.",
  "poll_url": "/api/agent-status/550e8400-e29b-41d4-a716-446655440000"
}
```

### Status Check (Polling Endpoint)
**Endpoint**: `GET /api/agent-status/{session_id}`  
**Polling Interval**: Every 2 seconds  
**Description**: Returns current workflow status and real-time events

```json
Response:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "current_stage": "Running CostCalculator",
  "progress": 50,
  "client_name": "Acme Corporation",
  "project_name": "E-commerce Platform Modernization",
  "industry": "Retail",
  "duration": "6 months",
  "team_size": 5,
  "requirements_data": {
    "raw_requirements": "...",
    "analyzed_requirements": {...}
  },
  "cost_data": {...},
  "agent_events": "[{\"type\":\"tool_call\",\"timestamp\":\"...\",\"action_group\":\"CostCalculator\",...}]",
  "template_paths": ["templates/proposal.pptx", "templates/sow.docx"],
  "document_urls": [],
  "error_message": null,
  "created_at": "2025-10-16T12:00:00.000Z",
  "updated_at": "2025-10-16T12:02:30.000Z"
}
```

### Results Retrieval
**Endpoint**: `GET /api/results/{session_id}`  
**Description**: Fetches generated documents and cost data after completion

```json
Response:
{
  "powerpoint_url": "https://s3.amazonaws.com/.../presentation_20251016.pptx",
  "sow_url": "https://s3.amazonaws.com/.../sow_20251016.docx",
  "cost_data": {
    "total_cost": 150000,
    "total_hours": 1200,
    "complexity_level": "High",
    "cost_breakdown": {
      "development": 80000,
      "design": 20000,
      "project_management": 30000,
      "qa_testing": 20000
    },
    "ai_insights": {
      "recommendations": "...",
      "risk_factors": [...],
      "optimization_opportunities": [...]
    }
  }
}
```

### Template Upload (Optional Feature)
**Endpoint**: `POST /api/upload-template`  
**Description**: Uploads custom templates to S3

```json
Request: (multipart/form-data)
file: <binary file data>

Response:
{
  "message": "Template uploaded successfully",
  "template_path": "templates/custom_proposal.pptx"
}
```

## Security Features

### Authentication & Authorization
- **AWS IAM**: Role-based access control with least privilege principle
- **Lambda Self-Invocation**: Restricted to own function ARN (wildcard pattern)
- **Bedrock Access**: Limited to specific foundation models and actions
- **S3 Buckets**: Private by default, presigned URLs for document access

### API Security
- **API Request Validation**: Input validation on all endpoints
- **CORS Configuration**: Configurable origins (wildcard for development)
- **Rate Limiting**: API Gateway throttling (10 req/s, 20 burst)
- **Error Handling**: No sensitive data in error messages

### Data Security
- **Encryption at Rest**: DynamoDB and S3 use AWS-managed encryption
- **Encryption in Transit**: TLS 1.2+ for all API communication
- **Session Isolation**: Each session has unique ID, no cross-session access
- **Temporary URLs**: Presigned S3 URLs expire after configurable duration

### Network Security
- **VPC**: Optional VPC deployment for Lambda functions
- **Private Subnets**: Bedrock API accessed via VPC endpoints (optional)
- **CloudFront**: DDoS protection and WAF integration (optional)

## Performance Characteristics

### Response Times
- **API Response Time**: < 500ms (session creation only)
- **Agent Workflow**: 3-5 minutes (background processing)
- **Status Polling**: 2-second intervals with < 100ms response
- **Document Generation**: 30-60 seconds per document

### Scalability
- **Lambda Concurrency**: 1000 concurrent executions (default limit)
- **API Gateway**: 10,000 requests/second (default limit)
- **DynamoDB**: On-demand scaling (unlimited read/write capacity)
- **S3**: Unlimited storage and requests
- **CloudFront**: Global edge locations for low latency

### Timeouts
- **Lambda Timeout**: 15 minutes (900 seconds) for async workflow
- **API Gateway Timeout**: 29 seconds (sync requests only)
- **DynamoDB Updates**: Rate-limited to 1/second per session
- **Bedrock Rate Limit**: 50+ RPM (Amazon Nova Pro)

### Resource Usage
- **Lambda Memory**:
  - SessionManager: 256 MB
  - Document Generators: 1024 MB
  - Other Functions: 256-512 MB
- **DynamoDB**: On-demand pricing (pay per request)
- **S3 Storage**: Lifecycle policies for old artifacts (optional)
- **CloudWatch Logs**: 7-day retention by default

## Cost Optimization

### AWS Service Costs (Estimated Monthly)
- **Lambda**: $10-50 (based on invocations and duration)
- **API Gateway**: $3-10 (based on requests)
- **DynamoDB**: $5-20 (on-demand pricing)
- **S3**: $1-5 (storage and requests)
- **CloudFront**: $5-15 (data transfer)
- **Bedrock**: Variable (based on token usage)

### Optimization Strategies
1. **On-Demand DynamoDB**: Avoid over-provisioning capacity
2. **S3 Lifecycle Policies**: Archive old documents to Glacier
3. **Lambda Memory Tuning**: Right-size memory allocations
4. **CloudWatch Log Retention**: Reduce to 3-7 days
5. **Amazon Nova Pro**: More cost-effective than Claude for high volume

## Contributing

### Guidelines
1. **Code Style**: Follow Vue 3 Composition API and Python PEP 8
2. **Status Constants**: Keep frontend and backend synchronized
3. **Testing**: Add tests for new Lambda functions
4. **Documentation**: Update README for new features
5. **Commits**: Use clear, descriptive commit messages

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and test locally
4. Ensure status constants match between frontend and backend
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request with detailed description
8. Wait for CI/CD checks to pass

### Testing Requirements
- Test async workflow locally before pushing
- Verify frontend-backend synchronization
- Check CloudWatch Logs for errors
- Validate CORS configuration
- Test polling behavior in browser

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **AWS Architecture**: Built following AWS serverless best practices
- **Amazon Bedrock**: Powered by Amazon Nova Pro foundation model
- **Design Inspiration**: Frontend UI inspired by Apple's design system
- **Async Pattern**: Based on AWS Lambda self-invocation best practices
- **ReAct Pattern**: Reasoning and Acting pattern from AI research

## Related Documentation

- [Frontend README](frontend/README.md) - Detailed frontend setup and architecture
- [Frontend Setup Guide](frontend/FRONTEND_SETUP.md) - Step-by-step frontend configuration
- [CDK README](cdk/README.md) - Infrastructure as code documentation
- [Scripts README](scripts/README.md) - Utility scripts documentation
- [Lambda READMEs](lambda/) - Individual Lambda function documentation

## Support & Issues

For issues, questions, or contributions:
1. Check existing GitHub Issues
2. Review troubleshooting section above
3. Check CloudWatch Logs for errors
4. Create a new issue with detailed description and logs

## Roadmap

Future enhancements planned:
- [ ] WebSocket support for real-time updates (alternative to polling)
- [ ] Multi-language support (i18n)
- [ ] Custom template editor
- [ ] PDF export for proposals
- [ ] Email notifications on completion
- [ ] Advanced analytics dashboard
- [ ] Team collaboration features
- [ ] Version control for proposals