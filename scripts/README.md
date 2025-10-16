# ScopeSmith Scripts

Utility scripts for deploying, configuring, and managing the ScopeSmith infrastructure and data.

## Overview

This directory contains Python scripts for:
- Bedrock Agent configuration
- Infrastructure validation
- Sample data seeding
- Template management
- Build automation

## Scripts

### 1. setup-agentcore.py

**Purpose**: Creates and configures the Bedrock Agent with action groups for all Lambda functions.

**What It Does**:
- Creates a new Bedrock Agent using Amazon Nova Pro
- Configures 5 action groups (RequirementsAnalyzer, CostCalculator, etc.)
- Creates agent alias for invocation
- Updates Lambda environment variables with agent IDs
- Prepares agent for workflow orchestration

**Usage**:
```bash
cd scripts
python setup-agentcore.py
```

**Prerequisites**:
- AWS credentials configured
- Lambda functions deployed via CDK
- Bedrock model access enabled in us-east-1

**What It Configures**:
```python
Agent Configuration:
- Name: ScopeSmith-Agent
- Foundation Model: amazon.nova-pro-v1:0
- Instructions: Project proposal generation workflow
- Idle Session TTL: 600 seconds

Action Groups (5):
1. RequirementsAnalyzer
   - Function: analyze_requirements
   - Lambda: ScopeSmithLambda-RequirementsAnalyzer
   
2. CostCalculator
   - Function: calculate_project_cost
   - Lambda: ScopeSmithLambda-CostCalculator
   
3. TemplateRetriever
   - Function: retrieve_templates
   - Lambda: ScopeSmithLambda-TemplateRetriever
   
4. PowerPointGenerator
   - Function: generate_powerpoint
   - Lambda: ScopeSmithLambda-PowerPointGenerator
   
5. SOWGenerator
   - Function: generate_sow
   - Lambda: ScopeSmithLambda-SOWGenerator
```

**Environment Variable Updates**:
Updates Session Manager Lambda with:
- `BEDROCK_AGENT_ID`: Created agent ID
- `BEDROCK_AGENT_ALIAS_ID`: Created alias ID (e.g., TSTALIASID)

**Output**:
```
✓ Agent created: ABCDEFGHIJ
✓ Action groups configured: 5
✓ Alias created: TSTALIASID
✓ Lambda environment updated
✓ Agent ready for use
```

### 2. seed-rate-sheets.py

**Purpose**: Seeds the DynamoDB rate sheets table with sample hourly rates for cost calculations.

**What It Does**:
- Populates rate sheets table with role-based hourly rates
- Provides default rates for cost calculator
- Supports multiple skill levels and roles

**Usage**:
```bash
cd scripts
python seed-rate-sheets.py
```

**Sample Data**:
```python
Rate Sheets:
- Senior Developer: $150/hr
- Junior Developer: $100/hr
- Project Manager: $120/hr
- Designer: $110/hr
- QA Engineer: $90/hr
- DevOps Engineer: $140/hr
- Business Analyst: $115/hr
```

**Prerequisites**:
- DynamoDB table deployed (ScopeSmithInfrastructure stack)
- AWS credentials configured

### 3. upload-sample-templates.py

**Purpose**: Uploads sample PowerPoint and SOW templates to S3 for document generation.

**What It Does**:
- Creates sample presentation templates
- Creates sample SOW document templates
- Uploads to S3 templates bucket
- Organizes templates by type and industry

**Usage**:
```bash
cd scripts
python upload-sample-templates.py
```

**Templates Created**:
```
s3://scopesmith-templates/
├── templates/
│   ├── default-proposal.pptx
│   ├── corporate-proposal.pptx
│   ├── tech-proposal.pptx
│   ├── healthcare-proposal.pptx
│   └── sow/
│       ├── default-sow.docx
│       ├── corporate-sow.docx
│       └── enterprise-sow.docx
```

**Prerequisites**:
- S3 buckets deployed (ScopeSmithInfrastructure stack)
- python-pptx and python-docx installed

### 4. validate-infrastructure.py

**Purpose**: Validates that all infrastructure components are properly deployed and configured.

**What It Does**:
- Checks DynamoDB tables exist and are active
- Verifies S3 buckets are accessible
- Tests Lambda functions are deployed
- Validates API Gateway endpoints
- Confirms Bedrock Agent configuration

**Usage**:
```bash
cd scripts
python validate-infrastructure.py
```

**Validation Checks**:
```
✓ DynamoDB Tables
  ✓ scopesmith-sessions (ACTIVE)
  ✓ scopesmith-rate-sheets (ACTIVE)

✓ S3 Buckets
  ✓ scopesmith-templates (accessible)
  ✓ scopesmith-artifacts (accessible)

✓ Lambda Functions
  ✓ SessionManager (configured)
  ✓ RequirementsAnalyzer (configured)
  ✓ CostCalculator (configured)
  ✓ TemplateRetriever (configured)
  ✓ PowerPointGenerator (configured)
  ✓ SOWGenerator (configured)

✓ API Gateway
  ✓ REST API deployed
  ✓ Endpoints active

✓ Bedrock Agent
  ✓ Agent exists
  ✓ Alias configured
  ✓ Lambda environment variables set
```

**Exit Codes**:
- `0`: All checks passed
- `1`: One or more checks failed

### 5. build.py

**Purpose**: Builds and packages Lambda functions with dependencies.

**What It Does**:
- Creates Lambda deployment packages
- Installs Python dependencies for each function
- Packages code with requirements
- Prepares for CDK deployment

**Usage**:
```bash
cd scripts
python build.py
```

**Process**:
```
For each Lambda function:
1. Create temporary build directory
2. Install requirements.txt dependencies
3. Copy function code
4. Create deployment package
5. Clean up temporary files
```

**Output**:
```
Building Lambda packages...
✓ session_manager packaged
✓ requirements_analyzer packaged
✓ cost_calculator packaged
✓ template_retriever packaged
✓ powerpoint_generator packaged
✓ sow_generator packaged
```

### 6. create_agentcore_gateway.py

**Purpose**: Legacy script for AgentCore Gateway setup (replaced by direct Bedrock Agent integration).

**Status**: Deprecated - Use `setup-agentcore.py` instead

**Note**: The project now uses native Bedrock Agents instead of AgentCore Gateway.

## Common Workflows

### Initial Setup
```bash
# 1. Deploy infrastructure
cd ../cdk
cdk deploy --all

# 2. Configure Bedrock Agent
cd ../scripts
python setup-agentcore.py

# 3. Seed data
python seed-rate-sheets.py

# 4. Upload templates
python upload-sample-templates.py

# 5. Validate everything
python validate-infrastructure.py
```

### Update Agent Configuration
```bash
cd scripts
python setup-agentcore.py --update
```

### Add Custom Templates
```bash
# Upload via AWS CLI
aws s3 cp my-template.pptx s3://scopesmith-templates/templates/

# Or modify upload-sample-templates.py and run
python upload-sample-templates.py
```

### Re-seed Rate Sheets
```bash
cd scripts
python seed-rate-sheets.py --overwrite
```

## Dependencies

See `requirements.txt`:
```
boto3>=1.28.0
python-pptx>=0.6.21
python-docx>=0.8.11
```

Install all dependencies:
```bash
cd scripts
pip install -r requirements.txt
```

## Environment Variables

Scripts use AWS credentials from:
- AWS CLI configuration (`~/.aws/credentials`)
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- IAM role (when running in AWS)

**Required Permissions**:
- Bedrock: Agent creation and management
- Lambda: Function updates and invocation
- DynamoDB: Table read/write
- S3: Bucket access and object uploads
- IAM: Pass role for agent execution

## Error Handling

### Common Issues

**Agent Creation Failed**:
```bash
Error: Bedrock model not accessible
Solution: Enable Amazon Nova Pro in Bedrock console (us-east-1)
```

**Lambda Update Failed**:
```bash
Error: Function not found
Solution: Deploy CDK Lambda stack first
```

**S3 Upload Failed**:
```bash
Error: Bucket does not exist
Solution: Deploy CDK Infrastructure stack first
```

**DynamoDB Seeding Failed**:
```bash
Error: Table not found
Solution: Deploy CDK Infrastructure stack first
```

## Logging

All scripts include detailed logging:
```python
[INFO] Starting Bedrock Agent setup...
[INFO] Creating agent: ScopeSmith-Agent
[SUCCESS] Agent created: ABCDEFGHIJ
[INFO] Configuring action groups...
[SUCCESS] Action group added: RequirementsAnalyzer
[WARNING] Alias already exists, updating...
[SUCCESS] Setup complete!
```

## Testing

### Test Individual Scripts
```bash
# Dry run mode (where available)
python setup-agentcore.py --dry-run
python upload-sample-templates.py --dry-run

# Validation only
python validate-infrastructure.py
```

### Integration Testing
```bash
# Full end-to-end setup
./scripts/full-setup.sh  # If available

# Or manual
python setup-agentcore.py
python seed-rate-sheets.py
python upload-sample-templates.py
python validate-infrastructure.py
```

## CI/CD Integration

These scripts are used in GitHub Actions workflows:

**deploy-infrastructure.yml**:
```yaml
- name: Configure Bedrock Agent
  run: python scripts/setup-agentcore.py

- name: Seed Data
  run: python scripts/seed-rate-sheets.py

- name: Upload Templates
  run: python scripts/upload-sample-templates.py

- name: Validate
  run: python scripts/validate-infrastructure.py
```

## Best Practices

1. **Run in Order**: Follow the setup workflow sequence
2. **Validate After Changes**: Always run validate-infrastructure.py
3. **Backup Data**: Export DynamoDB data before re-seeding
4. **Test Templates**: Validate templates before uploading
5. **Check Logs**: Review CloudWatch logs after script execution

## Troubleshooting

### Bedrock Agent Not Working
1. Check agent ID in Lambda environment variables
2. Verify action groups are configured
3. Test agent in Bedrock console
4. Check Lambda permissions for agent invocation

### Rate Sheets Not Loading
1. Verify table name matches
2. Check table has items
3. Validate DynamoDB permissions
4. Review cost calculator logs

### Templates Not Found
1. Verify S3 bucket name
2. Check template paths
3. Validate S3 permissions
4. Test template retriever function

## Related Documentation

- [Main README](../README.md) - Project overview
- [CDK README](../cdk/README.md) - Infrastructure deployment
- [Lambda Functions](../lambda/) - Function implementations

## Contributing

When adding new scripts:
1. Follow Python naming conventions
2. Include detailed docstrings
3. Add error handling and logging
4. Update this README
5. Test in development environment
6. Add to CI/CD workflows if needed
