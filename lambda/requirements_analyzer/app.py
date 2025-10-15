import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    """
    AgentCore Action Group Function for Requirements Analysis
    This function is invoked by the Bedrock Agent to analyze project requirements
    """
    try:
        # Parse input from AgentCore
        if 'inputText' in event:
            # Direct invocation from AgentCore
            input_text = event['inputText']
            session_id = event.get('sessionId')
            
            # Extract parameters from input text or event
            if 'parameters' in event:
                parameters = event['parameters']
                requirements = parameters.get('requirements', input_text)
                session_id = parameters.get('session_id', session_id)
            else:
                requirements = input_text
        else:
            # Legacy direct invocation support
            session_id = event['session_id']
            requirements = event['requirements']
        
        if not session_id:
            raise ValueError("Session ID is required")
        
        # Initialize AWS clients
        bedrock = boto3.client('bedrock-runtime')
        dynamodb = boto3.client('dynamodb')
        
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
        
        # Return response in AgentCore format
        return {
            'statusCode': 200,
            'body': json.dumps({
                'session_id': session_id,
                'message': 'Requirements analysis completed successfully',
                'analysis_result': analysis_result,
                'next_action': 'The requirements have been analyzed. You can now proceed with cost calculation using the analyze results.'
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
                'error': f'Requirements analysis failed: {str(e)}'
            })
        }