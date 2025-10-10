import os
import json
import boto3
from datetime import datetime
import tempfile
from pptx import Presentation
from pptx.util import Inches, Pt

def handler(event, context):
    try:
        session_id = event['session_id']
        template_path = event['template_path']
        proposal_data = event['proposal_data']
        
        s3 = boto3.client('s3')
        dynamodb = boto3.client('dynamodb')
        
        # Download template
        with tempfile.NamedTemporaryFile(suffix='.pptx') as template_file:
            s3.download_file(
                os.environ['TEMPLATES_BUCKET_NAME'],
                template_path,
                template_file.name
            )
            
            # Load presentation
            prs = Presentation(template_file.name)
            
            # Placeholder: Add slides based on proposal data
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            title = slide.shapes.title
            body = slide.shapes.placeholders[1]
            
            title.text = "Project Overview"
            tf = body.text_frame
            tf.text = json.dumps(proposal_data, indent=2)
            
            # Save modified presentation
            output_path = f"{session_id}/presentation.pptx"
            with tempfile.NamedTemporaryFile(suffix='.pptx') as output_file:
                prs.save(output_file.name)
                
                # Upload to S3
                s3.upload_file(
                    output_file.name,
                    os.environ['ARTIFACTS_BUCKET_NAME'],
                    output_path
                )
        
        # Generate presigned URL
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': os.environ['ARTIFACTS_BUCKET_NAME'],
                'Key': output_path
            },
            ExpiresIn=3600
        )
        
        # Update session with document URL
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET document_urls = list_append(if_not_exists(document_urls, :empty), :url), updated_at = :ua',
            ExpressionAttributeValues={
                ':url': {'L': [{'S': presigned_url}]},
                ':empty': {'L': []},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'session_id': session_id,
                'document_url': presigned_url
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }