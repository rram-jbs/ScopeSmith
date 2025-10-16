# Template Retriever Lambda

Bedrock Agent action group that retrieves and selects appropriate PowerPoint and SOW templates from S3 based on project requirements.

## Purpose

This Lambda function:
- Lists available templates in S3
- Selects appropriate templates based on project industry/type
- Returns template paths for document generation
- Supports custom template management

## How It Works

1. **Receives session ID** from Bedrock Agent
2. **Fetches session data** to understand project context
3. **Lists templates** from S3 bucket
4. **Selects best match** based on industry, complexity, or defaults
5. **Returns template paths** to Bedrock Agent
6. **Updates DynamoDB** with selected templates

## Input Format

```python
{
    'parameters': [
        {'name': 'session_id', 'value': 'uuid'},
        {'name': 'industry', 'value': 'Healthcare'},  # Optional
        {'name': 'template_type', 'value': 'corporate'}  # Optional
    ]
}
```

## Template Selection Logic

### By Industry
```python
industry_templates = {
    'Healthcare': 'templates/healthcare-proposal.pptx',
    'Finance': 'templates/finance-proposal.pptx',
    'Retail': 'templates/retail-proposal.pptx',
    'Technology': 'templates/tech-proposal.pptx'
}
```

### By Complexity
```python
complexity_templates = {
    'Low': 'templates/simple-proposal.pptx',
    'Medium': 'templates/standard-proposal.pptx',
    'High': 'templates/comprehensive-proposal.pptx'
}
```

### Default Fallback
```python
default_template = 'templates/default-proposal.pptx'
```

## S3 Template Structure

Templates are stored in S3 with this structure:

```
s3://scopesmith-templates/
├── templates/
│   ├── default-proposal.pptx
│   ├── corporate-proposal.pptx
│   ├── healthcare-proposal.pptx
│   ├── finance-proposal.pptx
│   ├── tech-proposal.pptx
│   └── sow/
│       ├── default-sow.docx
│       ├── corporate-sow.docx
│       └── enterprise-sow.docx
```

## Output Format

```python
{
    'messageVersion': '1.0',
    'response': {
        'actionGroup': 'TemplateRetriever',
        'function': 'templateretriever',
        'functionResponse': {
            'responseBody': {
                'TEXT': {
                    'body': '{
                        "session_id": "uuid",
                        "message": "Templates retrieved successfully",
                        "powerpoint_template": "templates/corporate-proposal.pptx",
                        "sow_template": "templates/sow/corporate-sow.docx"
                    }'
                }
            }
        }
    }
}
```

## Template Listing

```python
s3 = boto3.client('s3')

# List all templates
response = s3.list_objects_v2(
    Bucket=os.environ['TEMPLATES_BUCKET_NAME'],
    Prefix='templates/'
)

templates = [obj['Key'] for obj in response.get('Contents', [])]
```

## DynamoDB Updates

Stores selected template paths:

```python
dynamodb.update_item(
    TableName=os.environ['SESSIONS_TABLE_NAME'],
    Key={'session_id': {'S': session_id}},
    UpdateExpression='SET template_paths = :tp, #status = :status',
    ExpressionAttributeValues={
        ':tp': {'L': [
            {'S': powerpoint_template},
            {'S': sow_template}
        ]},
        ':status': {'S': 'TEMPLATES_SELECTED'}
    }
)
```

## Environment Variables

```bash
# S3 Buckets
TEMPLATES_BUCKET_NAME=scopesmith-templates

# DynamoDB
SESSIONS_TABLE_NAME=scopesmith-sessions
```

## Template Management

### Upload New Templates
Templates can be uploaded via:
1. AWS S3 Console
2. AWS CLI: `aws s3 cp template.pptx s3://scopesmith-templates/templates/`
3. Upload script: `scripts/upload-sample-templates.py`

### Template Requirements
- **PowerPoint**: .pptx format, compatible with python-pptx
- **SOW**: .docx format, compatible with python-docx
- **Naming**: Descriptive names (e.g., `healthcare-proposal.pptx`)

## Error Handling

### No Templates Found
```python
if not templates:
    return format_agent_response(200, {
        'message': 'No templates found, using default',
        'powerpoint_template': 'path/to/default.pptx',
        'sow_template': 'path/to/default-sow.docx'
    })
```

### S3 Access Errors
```python
except ClientError as e:
    print(f"[TEMPLATE RETRIEVER] S3 error: {str(e)}")
    return format_agent_response(500, f'Failed to access templates: {str(e)}')
```

## Status Updates

1. **SELECTING_TEMPLATES**: When starting retrieval
2. **TEMPLATES_SELECTED**: When templates chosen

## Dependencies

See `requirements.txt`:
```
boto3>=1.28.0
```

## Testing

```bash
python -c "
from app import handler
event = {
    'parameters': [
        {'name': 'session_id', 'value': 'test-session'},
        {'name': 'industry', 'value': 'Healthcare'}
    ]
}
print(handler(event, None))
"
```

## Performance

- **Typical execution**: < 1 second
- **S3 list operation**: 200-500ms
- **Template selection**: < 100ms
- **DynamoDB update**: < 100ms
- **Memory usage**: ~128 MB

## Logging

```
[TEMPLATE RETRIEVER] Received event: {...}
[TEMPLATE RETRIEVER] Retrieving templates for session: uuid
[TEMPLATE RETRIEVER] Found 8 templates in S3
[TEMPLATE RETRIEVER] Selected template: templates/healthcare-proposal.pptx
[TEMPLATE RETRIEVER] Templates selected successfully
```

## Integration with Workflow

This is the **third step** in the Bedrock Agent workflow:

```
RequirementsAnalyzer
    ↓
CostCalculator
    ↓
TemplateRetriever (this function)
    ↓
PowerPointGenerator (uses selected template)
    ↓
SOWGenerator (uses selected template)
```

## Deployment

Deployed via CDK LambdaStack as Bedrock Agent action group:
- **Timeout**: 30 seconds
- **Memory**: 256 MB
- **IAM Permissions**:
  - DynamoDB read/write
  - S3 read (list and get objects)

## Related Documentation

- [Main README](../../README.md) - Project overview
- [PowerPoint Generator](../powerpoint_generator/README.md) - Uses templates
- [Upload Templates Script](../../scripts/upload-sample-templates.py) - Template management
