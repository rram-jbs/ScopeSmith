import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    try:
        session_id = event['session_id']
        requirements = event['requirements']
        
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime')
        dynamodb = boto3.client('dynamodb')
        
        # Call Claude 3.5 Sonnet to analyze requirements
        response = bedrock.invoke_model(
            modelId=os.environ['BEDROCK_MODEL_ID'],
            contentType='application/json',
            body=json.dumps({
                "prompt": f"Analyze these project requirements and extract key components:\n{requirements}",
                "max_tokens": 2000
            })
        )
        
        analysis_result = json.loads(response['body'].read().decode())
        
        # Update DynamoDB
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET requirements_data = :rd, updated_at = :ua',
            ExpressionAttributeValues={
                ':rd': {'S': json.dumps(analysis_result)},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'session_id': session_id,
                'message': 'Requirements analysis complete'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }