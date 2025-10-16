# ScopeSmith

AI-powered proposal generation system using AWS Bedrock Agents.

## Architecture Overview

ScopeSmith uses a serverless architecture on AWS with the following components:

### Frontend
- **Framework**: Vue 3 + Vite
- **Styling**: Tailwind CSS with glassmorphic design
- **Hosting**: S3 + CloudFront
- **Key Features**:
  - Real-time agent orchestration viewer
  - 8-step workflow progress tracking
  - Live event streaming from Bedrock Agent

### Backend Infrastructure
- **API Gateway**: REST API with CORS support
- **Lambda Functions**: 
  - `SessionManager`: Handles session creation and Bedrock Agent invocation
  - `RequirementsAnalyzer`: Analyzes client requirements using Amazon Nova Pro
  - `CostCalculator`: Calculates project costs based on rate sheets
  - `TemplateRetriever`: Manages PowerPoint and SOW templates
  - `PowerPointGenerator`: Creates presentation documents
  - `SOWGenerator`: Generates Statement of Work documents
- **Bedrock Agent**: Orchestrates the workflow autonomously
- **DynamoDB**: Sessions and rate sheets storage
- **S3**: Template and artifact storage

## Frontend-Backend Synchronization

### API Endpoints (api_stack.py)
The frontend communicates with these endpoints:
- `POST /api/submit-assessment` → SessionManager Lambda
- `GET /api/agent-status/{session_id}` → SessionManager Lambda
- `GET /api/results/{session_id}` → SessionManager Lambda
- `POST /api/upload-template` → TemplateRetriever Lambda

### Status Values
The system uses these status values (synchronized across frontend and backend):
- `INITIATED`: Session created, agent starting
- `AGENT_PROCESSING`: Bedrock Agent is processing
- `COMPLETED`: All documents generated successfully
- `ERROR`: Agent execution failed
- `CONFIGURATION_ERROR`: Agent not properly configured

### Event Types
The `AgentStreamViewer` component handles these event types from the backend:
- `reasoning`: Agent's thought process (ReAct pattern)
- `tool_call`: Action group invocation with parameters
- `tool_response`: Lambda function response
- `chunk`: Streaming text from agent
- `warning`: Rate limiting or other warnings
- `final_response`: Agent's final output

### Workflow Step Mapping
The frontend workflow steps directly map to Lambda functions:
```javascript
{
  'RequirementsAnalyzer': 1,    // Analyze step
  'CostCalculator': 2,           // Calculate step
  'TemplateRetriever': 3,        // Templates step
  'PowerPointGenerator': 4,      // PowerPoint step
  'SOWGenerator': 5              // SOW step
}
```

## Deployment

### Prerequisites
- AWS Account with appropriate permissions
- GitHub repository with OIDC configured
- GitHub Secrets configured:
  - `AWS_ACCOUNT_ID`
  - `AWS_ROLE_ARN`

### Infrastructure Deployment
The `deploy-infrastructure.yml` workflow handles:
1. CDK stack deployment (Infrastructure, Lambda, API, Frontend)
2. AgentCore Gateway setup via `setup-agentcore.py`
3. Rate sheets seeding
4. Sample template uploads

### Frontend Deployment
The `deploy-frontend.yml` workflow:
1. Builds Vue application with environment variables
2. Syncs to S3 bucket
3. Invalidates CloudFront cache
4. Sets `VITE_API_BASE_URL` from CDK outputs

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
npm run build
# Upload dist/ to S3 bucket
```

## Development

### Local Frontend Development
```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in `.env.local` to your API Gateway URL.

### Testing Lambda Functions
```bash
cd lambda/session_manager
python -m pytest tests/
```

### Lambda Function Environment Variables
All Lambda functions expect:
- `SESSIONS_TABLE_NAME`: DynamoDB sessions table
- `BEDROCK_AGENT_ID`: Bedrock Agent ID (set by setup-agentcore.py)
- `BEDROCK_AGENT_ALIAS_ID`: Agent alias ID (set by setup-agentcore.py)
- `TEMPLATES_BUCKET_NAME`: S3 bucket for templates
- `ARTIFACTS_BUCKET_NAME`: S3 bucket for generated documents
- `RATE_SHEETS_TABLE_NAME`: DynamoDB rate sheets table (CostCalculator only)

## Agent Configuration

The Bedrock Agent uses:
- **Foundation Model**: Amazon Nova Pro (50+ RPM)
- **Action Groups**: 5 Lambda functions
- **Session Management**: DynamoDB for state persistence
- **Throttling Handling**: Exponential backoff with retry logic

## Monitoring

- **CloudWatch Logs**: All Lambda functions have structured logging
- **CloudWatch Alarms**: Error rate alerts via SNS
- **Agent Traces**: Bedrock Agent traces in CloudWatch
- **Frontend**: Real-time event streaming shows agent progress

## Troubleshooting

### Agent Configuration Errors
If you see `CONFIGURATION_ERROR`:
1. Check that `setup-agentcore.py` ran successfully
2. Verify `BEDROCK_AGENT_ID` and `BEDROCK_AGENT_ALIAS_ID` are set
3. Check Lambda function permissions for Bedrock

### Frontend Not Receiving Events
1. Verify API Gateway CORS configuration
2. Check `VITE_API_BASE_URL` environment variable
3. Ensure DynamoDB `agent_events` field is JSON string

### Rate Limiting
The system handles Bedrock API throttling automatically with:
- Exponential backoff in Lambda functions
- Batch DynamoDB updates (max 1/second)
- Warning events shown in UI

## Architecture Decisions

1. **Amazon Nova Pro**: Chosen for higher rate limits (50+ RPM vs 10 RPM for Claude)
2. **Bedrock Agent Gateway**: Uses action groups instead of direct Lambda invocation for ReAct orchestration
3. **Event Streaming**: DynamoDB stores full event stream for frontend polling
4. **Glassmorphic UI**: Modern design system with real-time progress visualization
5. **GitHub Actions**: Automated deployment pipeline with CDK

## Features

- 🤖 AI-powered requirements analysis
- 💰 Automated cost estimation based on role-specific rates
- 📊 Professional PowerPoint presentation generation
- 📄 Detailed Statement of Work (SOW) creation
- 🎨 Modern, responsive UI with real-time status updates
- 🔄 Template management system

## Tech Stack

### Frontend
- Vue.js 3 with Composition API
- Vite build system
- Tailwind CSS for styling
- Axios for API communication
- Real-time status updates with exponential backoff polling

### Backend
- Amazon Bedrock with Claude 3.5 Sonnet
- AWS Lambda for serverless compute
- Amazon DynamoDB for state management
- Amazon S3 for document storage
- AWS API Gateway for REST endpoints
- AWS CloudFront for content delivery

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Node.js 18+ and npm
3. Python 3.12
4. AWS CDK CLI v2.120.0 or later
5. Vue.js devtools (recommended for development)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/scopesmith.git
cd scopesmith
```

2. Install frontend dependencies:
```bash
cd frontend
npm install
```

3. Create a Python virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

4. Install backend dependencies:
```bash
cd cdk
pip install -r requirements.txt
```

5. Bootstrap CDK (if not already done):
```bash
cdk bootstrap
```

## Development

### Frontend Development
1. Start the development server:
```bash
cd frontend
npm run dev
```

2. Build for production:
```bash
npm run build
```

3. Lint and format code:
```bash
npm run lint
```

### Backend Development
1. Deploy infrastructure:
```bash
cd cdk
cdk deploy --all
```

2. Configure the environment:
```bash
cd ../scripts
python setup-agentcore.py
python seed-rate-sheets.py
python upload-sample-templates.py
```

3. Run infrastructure validation:
```bash
python validate-infrastructure.py
```

## Project Structure

```
scopesmith/
├── frontend/                      # Vue.js 3 Frontend
│   ├── src/
│   │   ├── components/           # Vue components
│   │   ├── composables/          # Vue composables
│   │   └── utils/                # Shared utilities
├── cdk/                          # Infrastructure as Code
├── lambda/                       # Serverless Functions
└── scripts/                      # Utility Scripts
```

## CI/CD

The project uses GitHub Actions for continuous integration and deployment:

### Workflows

1. **Infrastructure Deployment** (`deploy-infrastructure.yml`)
   - Triggers: Push to `main` branch (cdk/**, lambda/**, scripts/** changes)
   - Actions:
     - Deploys CDK stacks
     - Configures AgentCore
     - Seeds sample data
     - Uploads templates

2. **Frontend Deployment** (`deploy-frontend.yml`)
   - Triggers: Push to `main` branch (frontend/** changes)
   - Actions:
     - Builds Vue.js application
     - Deploys to S3
     - Invalidates CloudFront cache

3. **Lambda Testing** (`test-lambdas.yml`)
   - Triggers: Pull requests to `main` branch (lambda/** changes)
   - Actions:
     - Runs unit tests
     - Generates coverage reports
     - Uploads to Codecov

4. **Manual Infrastructure Destroy** (`manual-destroy.yml`)
   - Trigger: Manual workflow dispatch
   - Purpose: Safely tear down AWS infrastructure
   - Requires explicit confirmation

### Environment Variables

The workflows use the following secrets:
- `AWS_ROLE_ARN`: IAM role for AWS authentication
- `AWS_ACCOUNT_ID`: AWS account identifier

## API Reference

### Assessment Submission
POST `/api/submit-assessment`
```json
{
  "client_name": "string",
  "project_name": "string",
  "industry": "string",
  "requirements": "string",
  "duration": "string"
}
```

### Status Check
GET `/api/agent-status/{session_id}`
```json
{
  "status": "string",
  "current_stage": "string",
  "stage_details": {},
  "stage_timestamps": {}
}
```

### Results Retrieval
GET `/api/results/{session_id}`
```json
{
  "powerpoint_url": "string",
  "sow_url": "string",
  "cost_data": {
    "total_cost": "number",
    "breakdown": {}
  }
}
```

## Environment Variables

### Frontend (.env.development)
- `VITE_API_BASE_URL`: API endpoint URL
- `VITE_ENABLE_TEMPLATE_UPLOAD`: Feature flag for template uploads
- `VITE_MAX_FILE_SIZE`: Maximum upload file size
- `VITE_POLLING_INTERVAL`: Status check interval
- `VITE_MAX_POLLING_TIME`: Maximum polling duration

### Backend
- Managed through AWS Systems Manager Parameter Store
- Configured during CDK deployment

## Monitoring & Logging

- Real-time status tracking in the frontend
- CloudWatch Logs integration
- Error tracking and reporting
- Performance monitoring through CloudWatch metrics

## Security Features

- AWS IAM role-based access control
- API request validation
- CORS configuration
- Rate limiting
- Data encryption at rest and in transit

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes with clear messages
4. Open a pull request with detailed description

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built for the AWS AI Agent Hackathon 2025
- Powered by Amazon Bedrock and Claude 3.5 Sonnet
- Frontend UI inspired by modern design principles