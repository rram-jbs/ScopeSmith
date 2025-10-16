# PowerPoint Generator Lambda

Bedrock Agent action group that generates professional PowerPoint presentations using AI-generated content from Amazon Nova Pro and python-pptx library.

## Purpose

This Lambda function:
- Generates PowerPoint presentations from project data
- Uses AI to create compelling slide content
- Supports custom templates from S3
- Uploads presentations to S3 with presigned URLs
- Integrates full project context for relevant content

## How It Works

1. **Receives session ID and template path** from Bedrock Agent
2. **Fetches complete session data** (requirements, analysis, costs)
3. **Calls Amazon Nova Pro** to generate slide content
4. **Downloads template** from S3 (or creates blank presentation)
5. **Populates slides** using python-pptx
6. **Uploads to S3** and generates presigned URL
7. **Updates DynamoDB** with document URL

## Input Format

```python
{
    'parameters': [
        {'name': 'session_id', 'value': 'uuid'},
        {'name': 'template_path', 'value': 'templates/corporate.pptx'},
        {'name': 'proposal_data', 'value': '{"title": "..."}'}  # Optional
    ]
}
```

## AI-Generated Slide Structure

Amazon Nova Pro generates comprehensive slide content:

```json
{
    "slides": [
        {
            "title": "Executive Summary",
            "content": [
                "Project overview and objectives",
                "Key deliverables and timeline",
                "Investment and expected ROI"
            ],
            "notes": "Speaker notes for this slide"
        },
        {
            "title": "Project Scope",
            "content": [
                "Detailed scope description",
                "In-scope and out-of-scope items"
            ],
            "notes": "Discuss scope boundaries"
        },
        {
            "title": "Technical Approach",
            "content": [
                "Technology stack",
                "Architecture overview",
                "Integration points"
            ],
            "notes": "Technical details"
        }
    ]
}
```

## AI Prompt for Content Generation

Uses **full context** from the workflow:

```python
prompt = f"""Generate content for a professional PowerPoint presentation 
based on the following project information.

RAW PROJECT REQUIREMENTS (Original User Input):
{raw_requirements}

ANALYZED PROJECT DATA:
{json.dumps(analysis_data, indent=2)}

COST DATA:
{json.dumps(cost_data, indent=2)}

Create slides for a compelling project proposal presentation. 
Return as JSON (no markdown, no code blocks):
{{
    "slides": [
        {{
            "title": "Slide title",
            "content": ["Bullet point 1", "Bullet point 2"],
            "notes": "Speaker notes"
        }}
    ]
}}

Include slides for: Executive Summary, Project Scope, Technical Approach, 
Timeline, Team & Resources, Cost Breakdown, Benefits, and Next Steps."""
```

## Slide Generation with python-pptx

```python
from pptx import Presentation
from pptx.util import Inches, Pt

# Load template or create blank
prs = Presentation(template_path) if template_exists else Presentation()

# Add slides with content
for slide_data in slides_data.get('slides', []):
    slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title and Content
    
    # Set title
    slide.shapes.title.text = slide_data.get('title', 'Untitled Slide')
    
    # Add bullet points
    body = slide.shapes[1]
    tf = body.text_frame
    for idx, item in enumerate(slide_data.get('content', [])):
        if idx == 0:
            tf.text = str(item)
        else:
            p = tf.add_paragraph()
            p.text = str(item)
    
    # Add speaker notes
    if slide_data.get('notes'):
        slide.notes_slide.notes_text_frame.text = slide_data['notes']

# Save presentation
prs.save(output_file.name)
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
    prs = Presentation(template_file.name)
except s3.exceptions.NoSuchKey:
    # Template not found, create blank
    prs = Presentation()
```

### Supported Templates
- Corporate presentation templates (.pptx)
- Stored in S3 `TEMPLATES_BUCKET_NAME`
- Can include custom branding, colors, fonts

## S3 Upload and Presigned URL

```python
# Upload to S3
output_path = f"{session_id}/presentation.pptx"
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
        ':status': {'S': 'POWERPOINT_GENERATED'}
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
    print(f"[POWERPOINT] Template not found: {template_path}, creating blank")
    prs = Presentation()
```

### AI Response Parsing
```python
# Remove markdown code blocks
if '```json' in ppt_content:
    ppt_content = ppt_content.split('```json')[1].split('```')[0].strip()

# Parse JSON
slides_data = json.loads(ppt_content)
```

### Fallback Slides
```python
slides_data = {
    'slides': [
        {
            'title': 'Project Overview',
            'content': [analysis_data.get('project_scope', 'Project overview')],
            'notes': ''
        }
    ]
}
```

## Status Updates

1. **GENERATING_POWERPOINT**: When starting generation
2. **POWERPOINT_GENERATED**: When upload completes

## Dependencies

See `requirements.txt`:
```
boto3>=1.28.0
python-pptx>=0.6.21
```

## Testing

```bash
python -c "
from app import handler
event = {
    'parameters': [
        {'name': 'session_id', 'value': 'test-session'},
        {'name': 'template_path', 'value': 'templates/default.pptx'}
    ]
}
print(handler(event, None))
"
```

## Performance

- **Typical execution**: 5-8 seconds
- **Bedrock API call**: 3-5 seconds
- **Template download**: 1-2 seconds
- **Slide generation**: < 1 second
- **S3 upload**: 1-2 seconds
- **Memory usage**: ~256 MB (includes python-pptx)

## Logging

```
[POWERPOINT] Received event: {...}
[POWERPOINT] Generating presentation for session: uuid
[POWERPOINT] Calling Bedrock for presentation content generation...
[POWERPOINT] Using template: templates/corporate.pptx
[POWERPOINT] PowerPoint generated successfully
```

## Integration with Workflow

This is the **fourth step** in the Bedrock Agent workflow:

```
RequirementsAnalyzer
    ↓
CostCalculator
    ↓
TemplateRetriever
    ↓
PowerPointGenerator (this function)
    ↓
SOWGenerator
```

## Deployment

Deployed via CDK LambdaStack as Bedrock Agent action group:
- **Timeout**: 120 seconds (2 minutes for AI + template processing)
- **Memory**: 512 MB (python-pptx requires more memory)
- **IAM Permissions**:
  - DynamoDB read/write
  - S3 read (templates) and write (artifacts)
  - Bedrock model invocation

## Related Documentation

- [Main README](../../README.md) - Project overview
- [Template Retriever](../template_retriever/README.md) - Template selection
- [SOW Generator](../sow_generator/README.md) - Next step
