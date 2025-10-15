import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    try:
        print(f"[REQUIREMENTS ANALYZER] Received event: {json.dumps(event)}")
        
        # Check if this is a Bedrock Agent action group invocation
        if 'agent' in event or 'actionGroup' in event or 'function' in event:
            # This is a Bedrock Agent action group invocation
            print(f"[REQUIREMENTS ANALYZER] Bedrock Agent action group invocation detected")
            
            # Extract parameters from Bedrock Agent format
            parameters = event.get('parameters', [])
            param_dict = {}
            for param in parameters:
                param_dict[param['name']] = param['value']
            
            session_id = param_dict.get('session_id')
            requirements = param_dict.get('requirements')
            
        elif 'inputText' in event:
            # AgentCore Gateway invocation (legacy)
            try:
                params = json.loads(event['inputText'])
                session_id = params['session_id']
                requirements = params['requirements']
            except (json.JSONDecodeError, KeyError) as e:
                return format_agent_response(400, f'Invalid input format: {str(e)}')
        else:
            # Direct invocation
            session_id = event.get('session_id')
            requirements = event.get('requirements')

        if not session_id or not requirements:
            return format_agent_response(400, 'Missing required parameters: session_id and requirements')

        print(f"[REQUIREMENTS ANALYZER] Session ID: {session_id}")
        print(f"[REQUIREMENTS ANALYZER] Requirements length: {len(requirements)} characters")
        
        # Initialize AWS clients
        bedrock = boto3.client('bedrock-runtime')
        dynamodb = boto3.client('dynamodb')
        
        # Update status
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
        
        # Call Claude to analyze requirements
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
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read().decode())
        analysis_content = result.get('content', [{}])[0].get('text', '{}')
        
        try:
            analysis_result = json.loads(analysis_content)
        except json.JSONDecodeError:
            analysis_result = {
                "project_scope": "Requirements analysis completed",
                "deliverables": ["Custom software solution"],
                "technical_requirements": ["To be determined"],
                "timeline_estimate": "To be estimated",
                "complexity_level": "Medium",
                "team_skills_needed": ["Software development"],
                "key_risks": ["Scope changes"]
            }
        
        # Update DynamoDB
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
        
        # Return in Bedrock Agent action group format
        return format_agent_response(200, {
            'session_id': session_id,
            'message': 'Requirements analysis complete',
            'analysis_result': analysis_result
        })
        
    except Exception as e:
        print(f"[REQUIREMENTS ANALYZER] ERROR: {str(e)}")
        return format_agent_response(500, f'Analysis failed: {str(e)}')

def format_agent_response(status_code, body):
    """Format response for Bedrock Agent action group"""
    if isinstance(body, dict):
        body_text = json.dumps(body)
    else:
        body_text = str(body)
    
    # Bedrock Agent expects this specific format
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'RequirementsAnalyzer',
            'apiPath': '/analyze',
            'httpMethod': 'POST',
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': body_text
                }
            }
        }
    }