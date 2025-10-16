# Requirements Analyzer Lambda

Bedrock Agent action group that analyzes project requirements using Amazon Nova Pro to extract structured information.

## Purpose

This Lambda function is invoked by the Bedrock Agent to:
- Parse raw meeting notes and requirements
- Extract key project information using AI
- Structure data for downstream workflow steps
- Store analysis results in DynamoDB

## How It Works

1. **Receives raw requirements** from Bedrock Agent
2. **Calls Amazon Nova Pro** with structured prompt
3. **Extracts JSON** from AI response (handles markdown code blocks)
4. **Updates DynamoDB** with analysis results
5. **Returns formatted response** to Bedrock Agent

## Input Format

### Bedrock Agent Action Group Invocation
```python
{
    'parameters': [
        {'name': 'session_id', 'value': 'uuid'},
        {'name': 'requirements', 'value': 'Meeting notes...'}
    ]
}
```

### Direct Invocation (Legacy)
```python
{
    'session_id': 'uuid',
    'requirements': 'Meeting notes...'
}
```

## Output Format

### Success Response (Bedrock Agent Format)
```python
{
    'messageVersion': '1.0',
    'response': {
        'actionGroup': 'RequirementsAnalyzer',
        'function': 'requirementsanalyzer',
        'functionResponse': {
            'responseBody': {
                'TEXT': {
                    'body': '{
                        "session_id": "uuid",
                        "message": "Requirements analysis complete",
                        "analysis_result": {...}
                    }'
                }
            }
        }
    }
}
```

## Analysis Output Structure

The AI model generates structured analysis:

```json
{
    "project_scope": "Description of what the project entails",
    "deliverables": [
        "Mobile application",
        "Web dashboard",
        "API backend"
    ],
    "technical_requirements": [
        "React Native for mobile",
        "Node.js backend",
        "PostgreSQL database"
    ],
    "timeline_estimate": "6-9 months",
    "complexity_level": "High",
    "team_skills_needed": [
        "Full-stack developer",
        "Mobile developer",
        "DevOps engineer"
    ],
    "key_risks": [
        "Tight timeline",
        "Complex integrations",
        "Team availability"
    ]
}
```

## AI Prompt Structure

The function uses a carefully crafted prompt:

```python
prompt = f"""Analyze these project requirements and extract key information. 
Return ONLY a valid JSON object with the following structure 
(no markdown, no code blocks):
{{
    "project_scope": "Description of what the project entails",
    "deliverables": ["List of specific deliverables"],
    "technical_requirements": ["List of technical needs"],
    "timeline_estimate": "Estimated timeline",
    "complexity_level": "Low/Medium/High",
    "team_skills_needed": ["Required skills/roles"],
    "key_risks": ["Potential project risks"]
}}

Requirements to analyze:
{requirements}"""
```

## Amazon Nova Pro Integration

Uses Amazon Nova Pro (`amazon.nova-pro-v1:0`) for analysis:

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
            "max_new_tokens": 2000,
            "temperature": 0.7
        }
    })
)
```

### Why Nova Pro?

- **Higher rate limits**: 50+ RPM vs 10 RPM for Claude
- **Cost-effective**: Better pricing for this use case
- **Fast responses**: Typically 2-4 seconds
- **Structured output**: Reliable JSON generation

## DynamoDB Updates

Stores full requirements data with analysis:

```python
updated_requirements = {
    'raw_requirements': requirements,
    'analysis': analysis_result
}

dynamodb.update_item(
    TableName=os.environ['SESSIONS_TABLE_NAME'],
    Key={'session_id': {'S': session_id}},
    UpdateExpression='SET requirements_data = :rd, #status = :status',
    ExpressionAttributeValues={
        ':rd': {'S': json.dumps(updated_requirements)},
        ':status': {'S': 'REQUIREMENTS_ANALYZED'}
    }
)
```

## Error Handling

### JSON Parsing Errors
If AI returns markdown code blocks:
```python
if '```json' in analysis_content:
    analysis_content = analysis_content.split('```json')[1].split('```')[0].strip()
elif '```' in analysis_content:
    analysis_content = analysis_content.split('```')[1].split('```')[0].strip()
```

### Fallback Analysis
If parsing fails, uses sensible defaults:
```python
analysis_result = {
    "project_scope": f"Analysis of project requirements ({len(requirements)} characters provided)",
    "deliverables": ["Custom solution based on requirements"],
    "technical_requirements": ["To be refined during project planning"],
    "timeline_estimate": "To be estimated based on detailed analysis",
    "complexity_level": "Medium",
    "team_skills_needed": ["Software development", "Project management"],
    "key_risks": ["Scope changes", "Timeline constraints"]
}
```

## Environment Variables

```bash
# DynamoDB
SESSIONS_TABLE_NAME=scopesmith-sessions

# Bedrock
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

## Status Updates

The function updates session status through stages:

1. **ANALYZING_REQUIREMENTS**: When starting analysis
2. **REQUIREMENTS_ANALYZED**: When analysis completes

## Dependencies

See `requirements.txt`:
```
boto3>=1.28.0
```

## Testing

### Test with Sample Requirements
```bash
python -c "
from app import handler
event = {
    'session_id': 'test-session',
    'requirements': '''
        Build a mobile app for tracking fitness goals.
        Users should be able to log workouts, track nutrition,
        and view progress over time. Need iOS and Android support.
        Timeline: 4-6 months. Budget: $100k-150k.
    '''
}
print(handler(event, None))
"
```

### Test Bedrock Agent Format
```bash
python -c "
from app import handler
event = {
    'parameters': [
        {'name': 'session_id', 'value': 'test-session'},
        {'name': 'requirements', 'value': 'Build a CRM system...'}
    ]
}
print(handler(event, None))
"
```

## Performance

- **Typical execution**: 2-4 seconds
- **Bedrock API call**: 1.5-3 seconds
- **DynamoDB update**: < 100ms
- **Memory usage**: ~128 MB

## Logging

Structured logging with `[REQUIREMENTS ANALYZER]` prefix:

```
[REQUIREMENTS ANALYZER] Received event: {...}
[REQUIREMENTS ANALYZER] Session ID: uuid
[REQUIREMENTS ANALYZER] Requirements length: 500 characters
[REQUIREMENTS ANALYZER] Calling Bedrock model...
[REQUIREMENTS ANALYZER] Model response length: 800 chars
[REQUIREMENTS ANALYZER] Successfully parsed analysis result with 7 fields
[REQUIREMENTS ANALYZER] Analysis complete, updated DynamoDB
```

## Integration with Workflow

This is the **first step** in the Bedrock Agent workflow:

```
Session Created
    ↓
RequirementsAnalyzer (this function)
    ↓
CostCalculator (uses analysis)
    ↓
TemplateRetriever
    ↓
PowerPointGenerator (uses analysis)
    ↓
SOWGenerator (uses analysis)
```

## Context Preservation

The analysis is used by all downstream functions:
- **CostCalculator**: Uses complexity_level and deliverables for estimation
- **PowerPointGenerator**: Uses all fields for presentation content
- **SOWGenerator**: Uses scope and technical requirements for document

## Deployment

Deployed via CDK LambdaStack as Bedrock Agent action group:
- **Timeout**: 60 seconds
- **Memory**: 256 MB
- **IAM Permissions**:
  - DynamoDB read/write
  - Bedrock model invocation (`bedrock:InvokeModel`)

## Related Documentation

- [Main README](../../README.md) - Project overview
- [Session Manager](../session_manager/README.md) - Workflow orchestration
- [Cost Calculator](../cost_calculator/README.md) - Next step in workflow
