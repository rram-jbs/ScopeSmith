import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    try:
        session_id = event['session_id']
        template_type = event['template_type']
        
        s3 = boto3.client('s3')
        dynamodb = boto3.client('dynamodb')
        
        # List available templates
        response = s3.list_objects_v2(
            Bucket=os.environ['TEMPLATES_BUCKET_NAME'],
            Prefix=f"{template_type}/"
        )
        
        templates = []
        if 'Contents' in response:
            templates = [item['Key'] for item in response['Contents']]
        
        # For this example, we'll select the first template
        selected_template = templates[0] if templates else None
        
        if selected_template:
            # Update session with template path
            dynamodb.update_item(
                TableName=os.environ['SESSIONS_TABLE_NAME'],
                Key={'session_id': {'S': session_id}},
                UpdateExpression='SET template_paths = list_append(if_not_exists(template_paths, :empty), :tp), updated_at = :ua',
                ExpressionAttributeValues={
                    ':tp': {'L': [{'S': selected_template}]},
                    ':empty': {'L': []},
                    ':ua': {'S': datetime.utcnow().isoformat()}
                }
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'session_id': session_id,
                    'template_path': selected_template
                })
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'No templates found for type: {template_type}'
                })
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }