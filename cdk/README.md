# ScopeSmith CDK Infrastructure

AWS CDK infrastructure-as-code for the ScopeSmith AI proposal generation system.

## Overview

This directory contains the complete AWS infrastructure defined using AWS CDK (Cloud Development Kit) in Python. The infrastructure is split into four modular stacks for better organization and deployment control.

## Architecture

### Stack Structure

```
ScopeSmithInfrastructure  (Base resources)
    ↓
ScopeSmithLambda  (Lambda functions and permissions)
    ↓
ScopeSmithApi  (API Gateway endpoints)
    ↓
ScopeSmithFrontend  (S3 + CloudFront distribution)
```

## Stacks

### 1. InfrastructureStack (`stacks/infrastructure_stack.py`)

Base infrastructure resources:

- **DynamoDB Tables**:
  - `scopesmith-sessions`: Session state and workflow tracking
  - `scopesmith-rate-sheets`: Cost calculation rate data
  
- **S3 Buckets**:
  - `scopesmith-templates`: PowerPoint and SOW templates
  - `scopesmith-artifacts`: Generated documents (presentations, SOW)
  
- **CloudWatch Alarms**:
  - Error rate monitoring with SNS notifications
  - Threshold: 3 errors in 5 minutes

- **Exports**:
  - Table names and ARNs
  - Bucket names and ARNs
  - Used by dependent stacks

### 2. LambdaStack (`stacks/lambda_stack.py`)

All Lambda functions with Bedrock Agent integration:

#### Session Manager
- **Timeout**: 900 seconds (15 minutes)
- **Memory**: 512 MB
- **Special**: Lambda self-invocation permissions
- **Environment**:
  - `BEDROCK_AGENT_ID`: Set by setup-agentcore.py
  - `BEDROCK_AGENT_ALIAS_ID`: Set by setup-agentcore.py
  - `AWS_LAMBDA_FUNCTION_NAME`: Auto-set by Lambda

#### Action Group Functions
All have Bedrock model invocation permissions:

1. **RequirementsAnalyzer**
   - Timeout: 60 seconds
   - Memory: 256 MB
   - Model: `amazon.nova-pro-v1:0`

2. **CostCalculator**
   - Timeout: 60 seconds
   - Memory: 256 MB
   - Model: `amazon.nova-pro-v1:0`

3. **TemplateRetriever**
   - Timeout: 30 seconds
   - Memory: 256 MB
   - S3 read permissions

4. **PowerPointGenerator**
   - Timeout: 120 seconds
   - Memory: 512 MB
   - Dependencies: python-pptx
   - Model: `amazon.nova-pro-v1:0`

5. **SOWGenerator**
   - Timeout: 120 seconds
   - Memory: 512 MB
   - Dependencies: python-docx
   - Model: `amazon.nova-pro-v1:0`

### 3. ApiStack (`stacks/api_stack.py`)

API Gateway REST API:

- **Endpoints**:
  ```
  POST /api/submit-assessment      # Create session (< 500ms)
  GET  /api/agent-status/{id}      # Poll status (2s interval)
  GET  /api/results/{id}           # Fetch documents
  POST /api/upload-template        # Upload templates
  ```

- **Integration**:
  - Lambda proxy integration
  - Timeout: 29 seconds (API Gateway maximum)
  - Session Manager handles async workflow

- **CORS**:
  - Enabled for all origins (`*`)
  - Headers: Content-Type, Authorization, etc.
  - Methods: GET, POST, PUT, DELETE, OPTIONS

### 4. FrontendStack (`stacks/frontend_stack.py`)

Frontend hosting infrastructure:

- **S3 Bucket**:
  - Static website hosting
  - Public read access for website assets
  
- **CloudFront Distribution**:
  - Global CDN for fast delivery
  - HTTPS enforced
  - Default root object: `index.html`
  - Custom error responses (404 → index.html for SPA routing)

- **Outputs**:
  - CloudFront URL
  - S3 bucket name
  - Distribution ID

## Deployment

### Prerequisites

```bash
# Install CDK
npm install -g aws-cdk

# Install Python dependencies
cd cdk
pip install -r requirements.txt
```

### Deploy All Stacks

```bash
cd cdk

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cdk deploy --all

# Or deploy individually
cdk deploy ScopeSmithInfrastructure
cdk deploy ScopeSmithLambda
cdk deploy ScopeSmithApi
cdk deploy ScopeSmithFrontend
```

### Post-Deployment Setup

After deploying, configure the Bedrock Agent:

```bash
cd ../scripts
python setup-agentcore.py

# Seed rate sheets
python seed-rate-sheets.py

# Upload sample templates
python upload-sample-templates.py
```

## CDK Configuration

### cdk.json

```json
{
  "app": "python3 app.py",
  "context": {
    "@aws-cdk/core:enableStackNameDuplicates": "true",
    "aws-cdk:enableDiffNoFail": "true"
  }
}
```

### app.py

Main CDK application:

```python
from aws_cdk import App, Environment, Tags
from stacks.infrastructure_stack import InfrastructureStack
from stacks.lambda_stack import LambdaStack
from stacks.api_stack import ApiStack
from stacks.frontend_stack import FrontendStack

app = App()

# Define environment
env = Environment(region="us-east-1")

# Create stacks with dependencies
infra = InfrastructureStack(app, "ScopeSmithInfrastructure", env=env)
lambdas = LambdaStack(app, "ScopeSmithLambda", infra_stack=infra, env=env)
api = ApiStack(app, "ScopeSmithApi", lambda_stack=lambdas, env=env)
frontend = FrontendStack(app, "ScopeSmithFrontend", api_stack=api, env=env)

# Add tags
for stack in [infra, lambdas, api, frontend]:
    Tags.of(stack).add("Project", "ScopeSmith")
    Tags.of(stack).add("Environment", "dev")

app.synth()
```

## Key Features

### Asynchronous Architecture Support

The Lambda stack includes special configuration for the Session Manager:

```python
# Lambda self-invocation permission
session_manager_function.add_to_role_policy(
    PolicyStatement(
        actions=["lambda:InvokeFunction"],
        resources=[session_manager_function.function_arn]
    )
)
```

This enables the async workflow pattern without API Gateway timeouts.

### Bedrock Integration

All Lambda functions that use AI have:

```python
function.add_to_role_policy(
    PolicyStatement(
        actions=["bedrock:InvokeModel"],
        resources=[
            f"arn:aws:bedrock:{env.region}::foundation-model/amazon.nova-pro-v1:0"
        ]
    )
)
```

### Environment Variable Management

Environment variables are centrally managed:

```python
environment = {
    'SESSIONS_TABLE_NAME': infra_stack.sessions_table.table_name,
    'TEMPLATES_BUCKET_NAME': infra_stack.templates_bucket.bucket_name,
    'ARTIFACTS_BUCKET_NAME': infra_stack.artifacts_bucket.bucket_name,
    'BEDROCK_MODEL_ID': 'amazon.nova-pro-v1:0',
    'BEDROCK_AGENT_ID': 'PLACEHOLDER_AGENT_ID',  # Set by setup script
    'BEDROCK_AGENT_ALIAS_ID': 'PLACEHOLDER_ALIAS_ID'  # Set by setup script
}
```

## Stack Outputs

After deployment, CDK provides outputs:

```bash
Outputs:
ScopeSmithApi.ApiUrl = https://xxx.execute-api.us-east-1.amazonaws.com/prod
ScopeSmithFrontend.CloudFrontUrl = https://xxx.cloudfront.net
ScopeSmithFrontend.BucketName = scopesmith-frontend-xxx
ScopeSmithLambda.SessionManagerArn = arn:aws:lambda:...
```

These are used by:
- GitHub Actions workflows
- Frontend environment configuration
- Post-deployment scripts

## Testing CDK

```bash
# Synthesize CloudFormation templates
cdk synth

# Check for differences
cdk diff

# List all stacks
cdk list
```

## Cleanup

```bash
# Destroy all stacks (in reverse order)
cdk destroy ScopeSmithFrontend
cdk destroy ScopeSmithApi
cdk destroy ScopeSmithLambda
cdk destroy ScopeSmithInfrastructure

# Or use the manual workflow
# Via GitHub Actions: manual-destroy.yml
```

## Dependencies

See `requirements.txt`:

```
aws-cdk-lib>=2.100.0
constructs>=10.0.0
```

## Best Practices

1. **Stack Dependencies**: Use explicit dependencies to ensure proper ordering
2. **Resource Removal**: Set `removal_policy=RemovalPolicy.DESTROY` for dev
3. **Tagging**: Tag all resources for cost tracking and organization
4. **Exports**: Use CloudFormation exports for cross-stack references
5. **Environment Variables**: Centralize configuration in one place

## Monitoring

All stacks include CloudWatch integration:
- Lambda function logs
- API Gateway access logs
- CloudFront access logs
- DynamoDB metrics
- Custom metrics for error tracking

## Related Documentation

- [Main README](../README.md) - Project overview
- [Lambda Functions](../lambda/) - Function implementations
- [Scripts](../scripts/) - Deployment scripts
- [Frontend](../frontend/) - Frontend application
