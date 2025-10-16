# SOW Generator Lambda

Bedrock Agent action group that generates Statement of Work (SOW) documents using AI-generated content from Amazon Nova Pro and python-docx library.

## Purpose

This Lambda function:
- Generates professional SOW documents from project data
- Uses AI to create comprehensive contract sections
- Supports custom Word templates from S3
- Uploads documents to S3 with presigned URLs
- Integrates full project context for accurate legal/business content

## How It Works

1. **Receives session ID and template path** from Bedrock Agent
2. **Fetches complete session data** (requirements, analysis, costs)
3. **Calls Amazon Nova Pro** to generate SOW sections
4. **Downloads template** from S3 (or creates blank document)
5. **Populates document** using python-docx
6. **Uploads to S3** and generates presigned URL
7. **Updates DynamoDB** with document URL

## Input Format

```python
{
    'parameters': [
        {'name': 'session_id', 'value': 'uuid'},
        {'name': 'template_path', 'value': 'templates/sow/corporate-sow.docx'},
        {'name': 'sow_data', 'value': '{"title": "..."}'}  # Optional
    ]
}
```

## AI-Generated SOW Structure

Amazon Nova Pro generates comprehensive SOW sections:

```json
{
    "sections": [
        {
            "heading": "1. Project Overview",
            "content": "Detailed project description including objectives, background, and business context."
        },
        {
            "heading": "2. Scope of Work",
            "content": "Comprehensive scope including deliverables, milestones, and acceptance criteria."
        },
        {
            "heading": "3. Technical Requirements",
            "content": "Technical specifications, architecture, and integration requirements."
        },
        {
            "heading": "4. Project Timeline",
            "content": "Phased timeline with milestones and key dependencies."
        },
        {
            "heading": "5. Team and Resources",
            "content": "Team structure, roles, and resource allocation."
        },
        {
            "heading": "6. Cost and Payment Terms",
            "content": "Detailed cost breakdown and payment schedule."
        },
        {
            "heading": "7. Terms and Conditions",
            "content": "Legal terms, warranties, and limitations."
        }
    ]
}
```

## AI Prompt for Content Generation

Uses **full context** from the workflow:

```python
prompt = f"""Generate content for a professional Statement of Work (SOW) document 
based on the following project information.

RAW PROJECT REQUIREMENTS (Original User Input):
{raw_requirements}

ANALYZED PROJECT DATA:
{json.dumps(analysis_data, indent=2)}

COST DATA:
{json.dumps(cost_data, indent=2)}

Create a comprehensive SOW document with professional legal and business language. 
Return as JSON (no markdown, no code blocks):
{{
    "sections": [
        {{
            "heading": "1. Section Title",
            "content": "Section content in paragraph form"
        }}
    ]
}}

Include sections for: Project Overview, Scope of Work, Technical Requirements, 
Timeline, Team & Resources, Cost & Payment Terms, Terms & Conditions, and Acceptance Criteria."""
```

## Document Generation with python-docx

```python
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.style import WD_STYLE_TYPE

# Load template or create blank
doc = Document(template_path) if template_exists else Document()

# Add sections with content
for section_data in sow_sections.get('sections', []):
    # Add heading
    heading = doc.add_heading(section_data.get('heading', ''), level=1)
    
    # Add content paragraphs
    content = section_data.get('content', '')
    paragraphs = content.split('\n\n')  # Split into paragraphs
    for para_text in paragraphs:
        if para_text.strip():
            p = doc.add_paragraph(para_text.strip())
            p.style = 'Normal'

# Save document
doc.save(output_file.name)
```

## Template Handling

### Template Lookup
```python
# Check if template exists in S3
try:
    s3.head_object(
        Bucket=os.environ['TEMPLATES_BUCKET_NAME'],
        Key=template_path
    )
    # Download and use template
    doc = Document(template_file.name)
except s3.exceptions.NoSuchKey:
    # Template not found, create blank
    doc = Document()
```

### Supported Templates
- Word document templates (.docx)
- Stored in S3 `TEMPLATES_BUCKET_NAME/templates/sow/`
- Can include custom styles, headers, footers, logos

## S3 Upload and Presigned URL

```python
# Upload to S3
output_path = f"{session_id}/statement-of-work.docx"
s3.upload_file(
    output_file.name,
    os.environ['ARTIFACTS_BUCKET_NAME'],
    output_path
)

# Generate presigned URL (1 hour expiration)
presigned_url = s3.generate_presigned_url(
    'get_object',
    Params={
        'Bucket': os.environ['ARTIFACTS_BUCKET_NAME'],
        'Key': output_path
    },
    ExpiresIn=3600
)
```

## DynamoDB Updates

Appends document URL to session:

```python
dynamodb.update_item(
    TableName=os.environ['SESSIONS_TABLE_NAME'],
    Key={'session_id': {'S': session_id}},
    UpdateExpression='SET document_urls = list_append(if_not_exists(document_urls, :empty), :url), 
                      #status = :status',
    ExpressionAttributeValues={
        ':url': {'L': [{'S': presigned_url}]},
        ':empty': {'L': []},
        ':status': {'S': 'SOW_GENERATED'}
    }
)
```

## Environment Variables

```bash
# DynamoDB
SESSIONS_TABLE_NAME=scopesmith-sessions

# S3 Buckets
TEMPLATES_BUCKET_NAME=scopesmith-templates
ARTIFACTS_BUCKET_NAME=scopesmith-artifacts

# Bedrock
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

## Error Handling

### Template Not Found
```python
except s3.exceptions.NoSuchKey:
    print(f"[SOW] Template not found: {template_path}, creating blank document")
    doc = Document()
```

### AI Response Parsing
```python
# Remove markdown code blocks
if '```json' in sow_content:
    sow_content = sow_content.split('```json')[1].split('```')[0].strip()

# Parse JSON
sow_sections = json.loads(sow_content)
```

### Fallback Sections
```python
sow_sections = {
    'sections': [
        {
            'heading': '1. Project Overview',
            'content': analysis_data.get('project_scope', 'Project overview')
        },
        {
            'heading': '2. Cost Summary',
            'content': f"Total estimated cost: ${cost_data.get('total_cost', 0):,}"
        }
    ]
}
```

## Status Updates

1. **GENERATING_SOW**: When starting generation
2. **SOW_GENERATED**: When upload completes
3. **COMPLETED**: Final status after all documents generated

## Dependencies

See `requirements.txt`:
```
boto3>=1.28.0
python-docx>=0.8.11
```

## Testing

```bash
python -c "
from app import handler
event = {
    'parameters': [
        {'name': 'session_id', 'value': 'test-session'},
        {'name': 'template_path', 'value': 'templates/sow/default-sow.docx'}
    ]
}
print(handler(event, None))
"
```

## Performance

- **Typical execution**: 5-8 seconds
- **Bedrock API call**: 3-5 seconds
- **Template download**: 1-2 seconds
- **Document generation**: < 1 second
- **S3 upload**: 1-2 seconds
- **Memory usage**: ~256 MB (includes python-docx)

## Logging

```
[SOW] Received event: {...}
[SOW] Generating SOW for session: uuid
[SOW] Calling Bedrock for SOW content generation...
[SOW] Using template: templates/sow/corporate-sow.docx
[SOW] SOW generated successfully
```

## Integration with Workflow

This is the **final step** in the Bedrock Agent workflow:

```
RequirementsAnalyzer
    ↓
CostCalculator
    ↓
TemplateRetriever
    ↓
PowerPointGenerator
    ↓
SOWGenerator (this function)
    ↓
Session marked as COMPLETED
```

## Document Quality

The AI generates professional-quality content with:
- **Legal terminology**: Appropriate contract language
- **Business context**: Aligned with industry standards
- **Completeness**: All standard SOW sections included
- **Consistency**: Matches cost and scope from analysis

## Deployment

Deployed via CDK LambdaStack as Bedrock Agent action group:
- **Timeout**: 120 seconds (2 minutes for AI + template processing)
- **Memory**: 512 MB (python-docx requires more memory)
- **IAM Permissions**:
  - DynamoDB read/write
  - S3 read (templates) and write (artifacts)
  - Bedrock model invocation

## Related Documentation

- [Main README](../../README.md) - Project overview
- [Template Retriever](../template_retriever/README.md) - Template selection
- [PowerPoint Generator](../powerpoint_generator/README.md) - Previous step
