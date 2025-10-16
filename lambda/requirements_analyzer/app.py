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
            
            print(f"[REQUIREMENTS ANALYZER] Extracted parameters: {list(param_dict.keys())}")
            
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

        if not session_id:
            return format_agent_response(400, 'Missing required parameter: session_id')
        
        # If requirements not provided, try to fetch from DynamoDB session
        if not requirements:
            print(f"[REQUIREMENTS ANALYZER] Requirements not provided, fetching from session...")
            dynamodb = boto3.client('dynamodb')
            
            try:
                response = dynamodb.get_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}}
                )
                
                if 'Item' in response:
                    requirements_data = json.loads(response['Item'].get('requirements_data', {}).get('S', '{}'))
                    requirements = requirements_data.get('raw_requirements', '')
                    
                    if not requirements:
                        return format_agent_response(400, 'No requirements found in session')
                    
                    print(f"[REQUIREMENTS ANALYZER] Fetched requirements from session ({len(requirements)} chars)")
                else:
                    return format_agent_response(404, f'Session not found: {session_id}')
                    
            except Exception as e:
                print(f"[REQUIREMENTS ANALYZER] Error fetching session: {str(e)}")
                return format_agent_response(500, f'Failed to fetch session: {str(e)}')

        print(f"[REQUIREMENTS ANALYZER] Session ID: {session_id}")
        print(f"[REQUIREMENTS ANALYZER] Requirements length: {len(requirements)} characters")
        print(f"[REQUIREMENTS ANALYZER] Requirements preview: {requirements[:200]}...")
        
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
        
        # Call Amazon Nova Pro to analyze requirements
        prompt = f"""Analyze these project requirements and extract key information. Return ONLY a valid JSON object with the following structure (no markdown, no code blocks):
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
        
        print(f"[REQUIREMENTS ANALYZER] Calling Bedrock model...")
        
        response = bedrock.invoke_model(
            modelId=os.environ['BEDROCK_MODEL_ID'],
            contentType='application/json',
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": 2000,
                    "temperature": 0.7
                }
            })
        )
        
        result = json.loads(response['body'].read().decode())
        analysis_content = result.get('content', [{}])[0].get('text', '{}')
        
        print(f"[REQUIREMENTS ANALYZER] Model response length: {len(analysis_content)} chars")
        print(f"[REQUIREMENTS ANALYZER] Model response preview: {analysis_content[:500]}...")
        
        # Try to extract JSON from response (handle markdown code blocks)
        try:
            # Remove markdown code blocks if present
            if '```json' in analysis_content:
                analysis_content = analysis_content.split('```json')[1].split('```')[0].strip()
            elif '```' in analysis_content:
                analysis_content = analysis_content.split('```')[1].split('```')[0].strip()
            
            analysis_result = json.loads(analysis_content)
            print(f"[REQUIREMENTS ANALYZER] Successfully parsed analysis result")
            
        except json.JSONDecodeError as je:
            print(f"[REQUIREMENTS ANALYZER] Failed to parse JSON: {str(je)}")
            print(f"[REQUIREMENTS ANALYZER] Using fallback analysis")
            
            analysis_result = {
                "project_scope": f"Analysis of project requirements ({len(requirements)} characters provided)",
                "deliverables": ["Custom solution based on requirements"],
                "technical_requirements": ["To be refined during project planning"],
                "timeline_estimate": "To be estimated based on detailed analysis",
                "complexity_level": "Medium",
                "team_skills_needed": ["Software development", "Project management"],
                "key_risks": ["Scope changes", "Timeline constraints"]
            }
        
        # Update DynamoDB with full requirements data
        updated_requirements = {
            'raw_requirements': requirements,
            'analysis': analysis_result
        }
        
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET requirements_data = :rd, #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':rd': {'S': json.dumps(updated_requirements)},
                ':status': {'S': 'REQUIREMENTS_ANALYZED'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        print(f"[REQUIREMENTS ANALYZER] Analysis complete, updated DynamoDB")
        
        # Return in Bedrock Agent action group format
        return format_agent_response(200, {
            'session_id': session_id,
            'message': 'Requirements analysis complete',
            'analysis_result': analysis_result
        })
        
    except Exception as e:
        print(f"[REQUIREMENTS ANALYZER] ERROR: {str(e)}")
        import traceback
        print(f"[REQUIREMENTS ANALYZER] Traceback: {traceback.format_exc()}")
        return format_agent_response(500, f'Analysis failed: {str(e)}')

def format_agent_response(status_code, body):
    """Format response for Bedrock Agent action group"""
    if isinstance(body, dict):
        body_text = json.dumps(body)
    else:
        body_text = str(body)
    
    # Bedrock Agent expects this specific format
    # The apiPath and function must match what was defined in the action group
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'RequirementsAnalyzer',
            'function': 'requirementsanalyzer',  # Must match function name in action group
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': body_text
                    }
                }
            }
        }
    }