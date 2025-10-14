import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    try:
        session_id = event['session_id']
        requirements = event['requirements']
        
        # Initialize AWS clients
        bedrock = boto3.client('bedrock-runtime')
        dynamodb = boto3.client('dynamodb')
        lambda_client = boto3.client('lambda')
        
        # Update status to analyzing
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'ANALYZING_REQUIREMENTS'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Call Claude 3.5 Sonnet to analyze requirements
        prompt = f"""Analyze these project requirements and extract key information. Return a JSON response with the following structure:
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
        
        response = bedrock.invoke_model(
            modelId=os.environ['BEDROCK_MODEL_ID'],
            contentType='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        result = json.loads(response['body'].read().decode())
        analysis_content = result.get('content', [{}])[0].get('text', '{}')
        
        # Parse the analysis result
        try:
            analysis_result = json.loads(analysis_content)
        except json.JSONDecodeError:
            # Fallback if Claude didn't return valid JSON
            analysis_result = {
                "project_scope": "Requirements analysis completed",
                "deliverables": ["Custom software solution"],
                "technical_requirements": ["To be determined"],
                "timeline_estimate": "To be estimated",
                "complexity_level": "Medium",
                "team_skills_needed": ["Software development"],
                "key_risks": ["Scope changes"]
            }
        
        # Update DynamoDB with analysis results
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET requirements_data = :rd, #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':rd': {'S': json.dumps(analysis_result)},
                ':status': {'S': 'REQUIREMENTS_ANALYZED'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Invoke cost calculator with the analysis results
        if os.environ.get('COST_CALCULATOR_ARN'):
            lambda_client.invoke(
                FunctionName=os.environ['COST_CALCULATOR_ARN'],
                InvocationType='Event',
                Payload=json.dumps({
                    'session_id': session_id,
                    'requirements_data': analysis_result
                })
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'session_id': session_id,
                'message': 'Requirements analysis complete',
                'analysis_result': analysis_result
            })
        }
        
    except Exception as e:
        # Update session with error status
        try:
            dynamodb = boto3.client('dynamodb')
            dynamodb.update_item(
                TableName=os.environ['SESSIONS_TABLE_NAME'],
                Key={'session_id': {'S': session_id}},
                UpdateExpression='SET #status = :status, error_message = :error, updated_at = :ua',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': 'ERROR'},
                    ':error': {'S': f'Requirements analysis failed: {str(e)}'},
                    ':ua': {'S': datetime.utcnow().isoformat()}
                }
            )
        except:
            pass
            
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }