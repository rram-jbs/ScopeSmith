import os
import json
import boto3
from datetime import datetime
import tempfile
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def handler(event, context):
    try:
        # Handle AgentCore Gateway calls only
        if 'inputText' in event:
            try:
                params = json.loads(event['inputText'])
                session_id = params['session_id']
                template_path = params.get('template_path')
                proposal_data = params.get('proposal_data')
                if isinstance(proposal_data, str):
                    proposal_data = json.loads(proposal_data)
            except (json.JSONDecodeError, KeyError) as e:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Invalid input format from AgentCore: {str(e)}'
                    })
                }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters'
                })
            }

        print(f"[SOW GENERATOR] Generating SOW document for session: {session_id}")
        
        s3 = boto3.client('s3')
        dynamodb = boto3.client('dynamodb')
        
        # Download template
        with tempfile.NamedTemporaryFile(suffix='.docx') as template_file:
            s3.download_file(
                os.environ['TEMPLATES_BUCKET_NAME'],
                template_path,
                template_file.name
            )
            
            # Load document
            doc = Document(template_file.name)
            
            # Placeholder: Add SOW content based on proposal data
            doc.add_heading('Statement of Work', 0)
            
            doc.add_heading('1. Project Overview', level=1)
            doc.add_paragraph(proposal_data.get('project_overview', ''))
            
            doc.add_heading('2. Scope of Services', level=1)
            services = proposal_data.get('services', [])
            for service in services:
                doc.add_paragraph(service, style='List Bullet')
            
            doc.add_heading('3. Timeline', level=1)
            doc.add_paragraph(proposal_data.get('timeline', ''))
            
            doc.add_heading('4. Deliverables', level=1)
            deliverables = proposal_data.get('deliverables', [])
            for deliverable in deliverables:
                doc.add_paragraph(deliverable, style='List Number')
            
            doc.add_heading('5. Cost Breakdown', level=1)
            costs = proposal_data.get('costs', {})
            table = doc.add_table(rows=1, cols=3)
            table.style = 'Table Grid'
            header_cells = table.rows[0].cells
            header_cells[0].text = 'Item'
            header_cells[1].text = 'Description'
            header_cells[2].text = 'Cost'
            
            for item, details in costs.items():
                row_cells = table.add_row().cells
                row_cells[0].text = item
                row_cells[1].text = details.get('description', '')
                row_cells[2].text = f"${details.get('amount', 0):,.2f}"
            
            # Save modified document
            output_path = f"{session_id}/sow.docx"
            with tempfile.NamedTemporaryFile(suffix='.docx') as output_file:
                doc.save(output_file.name)
                
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
                'message': 'SOW generated successfully',
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