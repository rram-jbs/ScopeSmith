# Cost Calculator Lambda

Bedrock Agent action group that calculates project costs based on requirements analysis and provides AI-powered cost insights using Amazon Nova Pro.

## Purpose

This Lambda function:
- Calculates project costs based on analyzed requirements
- Uses AI to validate cost estimates and provide recommendations
- Breaks down costs by role (developers, PM, designer, QA)
- Identifies hidden costs and cost-saving opportunities
- Stores cost data in DynamoDB for proposal generation

## How It Works

1. **Receives requirements data** from Bedrock Agent
2. **Calculates baseline costs** using complexity and deliverables
3. **Calls Amazon Nova Pro** for cost validation and insights
4. **Combines calculations** with AI recommendations
5. **Updates DynamoDB** with complete cost data
6. **Returns formatted response** to Bedrock Agent

## Input Format

### Bedrock Agent Action Group Invocation
```python
{
    'parameters': [
        {'name': 'session_id', 'value': 'uuid'},
        {'name': 'requirements_data', 'value': '{"complexity_level": "High", ...}'}
    ]
}
```

## Cost Calculation Logic

### Base Hours Calculation
```python
base_hours = max(80, deliverables_count * 40 + technical_requirements_count * 20)
```

### Complexity Multipliers
```python
complexity_multipliers = {
    "Low": 1.0,
    "Medium": 1.5,
    "High": 2.0
}
total_hours = int(base_hours * complexity_multiplier)
```

### Role Allocation (Default Rates)
```python
default_rates = {
    "senior_developer": 150,    # 40% of hours
    "junior_developer": 100,    # 30% of hours
    "project_manager": 120,     # 15% of hours
    "designer": 110,            # 10% of hours
    "qa_engineer": 90           # 5% of hours
}
```

## Output Structure

### Cost Breakdown
```json
{
    "total_hours": 1200,
    "total_cost": 150000,
    "complexity_level": "High",
    "cost_breakdown": {
        "senior_developer": {
            "hours": 480,
            "rate": 150,
            "amount": 72000
        },
        "junior_developer": {
            "hours": 360,
            "rate": 100,
            "amount": 36000
        },
        "project_manager": {
            "hours": 180,
            "rate": 120,
            "amount": 21600
        },
        "designer": {
            "hours": 120,
            "rate": 110,
            "amount": 13200
        },
        "qa_engineer": {
            "hours": 60,
            "rate": 90,
            "amount": 5400
        }
    },
    "ai_insights": {
        "resource_allocation_recommendations": [
            "Consider adding a DevOps engineer for infrastructure setup",
            "Frontend and backend work can be parallelized"
        ],
        "risk_contingency_percentage": "15",
        "hidden_costs_to_consider": [
            "Third-party API integrations",
            "Cloud infrastructure costs",
            "Testing and QA tools"
        ],
        "cost_saving_opportunities": [
            "Use open-source libraries where possible",
            "Consider offshore team members for cost reduction"
        ],
        "overall_assessment": "Cost estimate is reasonable for a high-complexity project"
    }
}
```

## AI Prompt for Cost Validation

Uses Amazon Nova Pro with **full context**:

```python
prompt = f"""Analyze this project data and provide a cost breakdown validation and recommendations.

RAW PROJECT REQUIREMENTS (Original User Input):
{raw_requirements}

ANALYZED PROJECT DATA:
{json.dumps(analysis_data, indent=2)}

CALCULATED COST ESTIMATES:
{json.dumps(cost_result, indent=2)}

Based on the complete project context, provide recommendations in JSON format 
with the following structure (no markdown, no code blocks):
{{
    "resource_allocation_recommendations": ["List of recommendations"],
    "risk_contingency_percentage": "Recommended percentage as number (e.g., 15)",
    "hidden_costs_to_consider": ["List of potential hidden costs"],
    "cost_saving_opportunities": ["List of opportunities"],
    "overall_assessment": "Brief assessment of the cost estimate accuracy"
}}"""
```

## Amazon Nova Pro Integration

```python
bedrock.invoke_model(
    modelId=os.environ['BEDROCK_MODEL_ID'],
    contentType='application/json',
    body=json.dumps({
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 1500,
            "temperature": 0.5
        }
    })
)
```

### Temperature Setting
- **0.5**: More conservative and consistent recommendations
- Lower than requirements analysis (0.7) for cost reliability

## Context Preservation

The function includes **both** raw requirements and analysis:

```python
requirements_data_full = json.loads(requirements_data_str)
raw_requirements = requirements_data_full.get('raw_requirements', '')
analysis_data = requirements_data_full.get('analysis', {})
```

This ensures the AI has complete context for accurate cost insights.

## DynamoDB Updates

```python
dynamodb.update_item(
    TableName=os.environ['SESSIONS_TABLE_NAME'],
    Key={'session_id': {'S': session_id}},
    UpdateExpression='SET cost_data = :cd, #status = :status',
    ExpressionAttributeValues={
        ':cd': {'S': json.dumps(cost_result)},
        ':status': {'S': 'COSTS_CALCULATED'}
    }
)
```

## Error Handling

### JSON Parsing (Nested Parameters)
```python
if param_name == 'requirements_data':
    try:
        if isinstance(param_value, str):
            param_dict[param_name] = json.loads(param_value)
        else:
            param_dict[param_name] = param_value
    except json.JSONDecodeError as e:
        print(f"[COST CALCULATOR] JSON decode error: {str(e)}")
```

### AI Response Parsing
```python
# Remove markdown code blocks
if '```json' in ai_insights_content:
    ai_insights_content = ai_insights_content.split('```json')[1].split('```')[0].strip()
elif '```' in ai_insights_content:
    ai_insights_content = ai_insights_content.split('```')[1].split('```')[0].strip()

# Parse JSON
ai_insights = json.loads(ai_insights_content)
```

### Fallback Insights
```python
ai_insights = {
    "overall_assessment": "Cost calculation completed based on project analysis",
    "risk_contingency_percentage": "15",
    "resource_allocation_recommendations": ["Review resource allocation"],
    "hidden_costs_to_consider": ["Infrastructure", "Training", "Maintenance"],
    "cost_saving_opportunities": ["Optimize resource utilization"]
}
```

## Environment Variables

```bash
# DynamoDB
SESSIONS_TABLE_NAME=scopesmith-sessions
RATE_SHEETS_TABLE_NAME=scopesmith-rate-sheets  # Future use

# Bedrock
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

## Status Updates

1. **CALCULATING_COSTS**: When starting calculation
2. **COSTS_CALCULATED**: When calculation completes

## Dependencies

See `requirements.txt`:
```
boto3>=1.28.0
```

## Testing

### Test with Sample Data
```bash
python -c "
from app import handler
event = {
    'parameters': [
        {'name': 'session_id', 'value': 'test-session'},
        {'name': 'requirements_data', 'value': '{
            \"complexity_level\": \"High\",
            \"deliverables\": [\"Mobile App\", \"Web Dashboard\", \"API\"],
            \"technical_requirements\": [\"React Native\", \"Node.js\", \"PostgreSQL\"]
        }'}
    ]
}
print(handler(event, None))
"
```

## Performance

- **Typical execution**: 3-5 seconds
- **Calculation time**: < 100ms
- **Bedrock API call**: 2-4 seconds
- **DynamoDB update**: < 100ms
- **Memory usage**: ~128 MB

## Logging

```
[COST CALCULATOR] Received event: {...}
[COST CALCULATOR] Starting cost calculation for session: uuid
[COST CALCULATOR] Calling Bedrock model for cost validation...
[COST CALCULATOR] Bedrock response received
[COST CALCULATOR] Cost calculation complete
```

## Integration with Workflow

This is the **second step** in the Bedrock Agent workflow:

```
RequirementsAnalyzer
    ↓
CostCalculator (this function)
    ↓
TemplateRetriever
    ↓
PowerPointGenerator (uses cost data)
    ↓
SOWGenerator (uses cost data)
```

## Recent Fixes

### Issue: Bedrock Client Not Initialized
**Before:**
```python
# bedrock was used before being initialized
response = bedrock.invoke_model(...)
```

**After:**
```python
bedrock = boto3.client('bedrock-runtime')
response = bedrock.invoke_model(...)
```

### Issue: JSON Parsing in Parameters
**Before:**
```python
# String not parsed properly
requirements_data = param_dict.get('requirements_data')
```

**After:**
```python
# Proper nested JSON parsing
if isinstance(param_value, str):
    param_dict[param_name] = json.loads(param_value)
```

## Deployment

Deployed via CDK LambdaStack as Bedrock Agent action group:
- **Timeout**: 60 seconds
- **Memory**: 256 MB
- **IAM Permissions**:
  - DynamoDB read/write
  - Bedrock model invocation

## Related Documentation

- [Main README](../../README.md) - Project overview
- [Requirements Analyzer](../requirements_analyzer/README.md) - Previous step
- [PowerPoint Generator](../powerpoint_generator/README.md) - Uses cost data
