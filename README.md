# ScopeSmith

An intelligent proposal generation system powered by Amazon Bedrock AgentCore, designed to automate the creation of technical proposals and statements of work.

## Overview

ScopeSmith streamlines the proposal creation process by leveraging AI to analyze requirements, calculate accurate costs, and generate professional documentation. Built with Vue.js 3, Tailwind CSS, and AWS serverless technologies.

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