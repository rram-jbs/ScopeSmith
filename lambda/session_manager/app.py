import os
import json
import boto3
import uuid
from datetime import datetime

def create_session(client_name, project_name, industry, requirements, duration, team_size):
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    dynamodb = boto3.client('dynamodb')
    dynamodb.put_item(
        TableName=os.environ['SESSIONS_TABLE_NAME'],
        Item={
            'session_id': {'S': session_id},
            'status': {'S': 'INITIATED'},
            'client_name': {'S': client_name},
            'project_name': {'S': project_name},
            'industry': {'S': industry},
            'duration': {'S': duration},
            'team_size': {'N': str(team_size)},
            'requirements_data': {'S': json.dumps({
                'raw_requirements': requirements
            })},
            'created_at': {'S': timestamp},
            'updated_at': {'S': timestamp}
        }
    )
    return session_id

def get_session_status(session_id):
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.get_item(
        TableName=os.environ['SESSIONS_TABLE_NAME'],
        Key={'session_id': {'S': session_id}}
    )
    
    if 'Item' not in response:
        return None
        
    item = response['Item']
    return {
        'session_id': item['session_id']['S'],
        'status': item['status']['S'],
        'client_name': item['client_name']['S'],
        'project_name': item['project_name']['S'],
        'industry': item['industry']['S'],
        'duration': item['duration']['S'],
        'team_size': int(item['team_size']['N']),
        'requirements_data': json.loads(item.get('requirements_data', {}).get('S', '{}')),
        'cost_data': json.loads(item.get('cost_data', {}).get('S', '{}')),
        'template_paths': [p['S'] for p in item.get('template_paths', {}).get('L', [])],
        'document_urls': [url['S'] for url in item.get('document_urls', {}).get('L', [])],
        'error_message': item.get('error_message', {}).get('S', None),
        'created_at': item['created_at']['S'],
        'updated_at': item['updated_at']['S']
    }

def invoke_bedrock_agent(session_id, client_name, project_name, industry, requirements, duration, team_size):
    """Invoke the Bedrock Agent to start the AI-orchestrated workflow (Phase 2)"""
    try:
        print(f"[BEDROCK AGENT] Starting invocation for session: {session_id}")
        print(f"[BEDROCK AGENT] Agent ID: {os.environ.get('BEDROCK_AGENT_ID', 'NOT_SET')}")
        print(f"[BEDROCK AGENT] Agent Alias ID: {os.environ.get('BEDROCK_AGENT_ALIAS_ID', 'NOT_SET')}")
        
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        
        # Create the input text for the agent
        input_text = f"""Please analyze the following client requirements and generate a comprehensive proposal:

Client Information:
- Client Name: {client_name}
- Project Name: {project_name}
- Industry: {industry}
- Project Duration: {duration}
- Team Size: {team_size}

Requirements:
{requirements}

Session ID: {session_id}

Please perform the following tasks in sequence:
1. Analyze the requirements and break them down into deliverables, technical requirements, and complexity assessment
2. Calculate project costs based on the analyzed requirements using standard rate sheets
3. Retrieve appropriate document templates for both PowerPoint presentation and Statement of Work
4. Generate a customized PowerPoint presentation with the proposal details
5. Create a detailed Statement of Work document

Please coordinate these tasks intelligently and update the session status as you progress through each stage."""

        print(f"[BEDROCK AGENT] Sending input text (length: {len(input_text)} chars)")
        
        # Invoke the Bedrock Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=os.environ['BEDROCK_AGENT_ID'],
            agentAliasId=os.environ['BEDROCK_AGENT_ALIAS_ID'],
            sessionId=session_id,
            inputText=input_text
        )
        
        print(f"[BEDROCK AGENT] ✓ Invocation successful for session: {session_id}")
        print(f"[BEDROCK AGENT] Response type: {type(response)}")
        print(f"[BEDROCK AGENT] Response keys: {response.keys() if hasattr(response, 'keys') else 'N/A'}")
        print(f"[BEDROCK AGENT] Full response: {json.dumps(response, default=str, indent=2)}")
        
        return response
        
    except Exception as e:
        print(f"[BEDROCK AGENT] ✗ ERROR invoking Bedrock Agent for session {session_id}: {str(e)}")
        print(f"[BEDROCK AGENT] Error type: {type(e).__name__}")
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
                    ':error': {'S': f'AgentCore invocation failed: {str(e)}'},
                    ':ua': {'S': datetime.utcnow().isoformat()}
                }
            )
            print(f"[BEDROCK AGENT] Updated session {session_id} with ERROR status")
        except Exception as update_error:
            print(f"[BEDROCK AGENT] Failed to update session with error status: {str(update_error)}")
        raise e

def create_cors_response(status_code, body):
    """Helper function to create response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body) if isinstance(body, dict) else body
    }

def handler(event, context):
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        # Handle preflight OPTIONS requests
        if http_method == 'OPTIONS':
            return create_cors_response(200, {'message': 'OK'})
        
        if http_method == 'POST' and path == '/api/submit-assessment':
            body = json.loads(event['body'])
            session_id = create_session(
                client_name=body['client_name'],
                project_name=body.get('project_name', ''),
                industry=body.get('industry', ''),
                requirements=body['requirements'],
                duration=body.get('duration', ''),
                team_size=body.get('team_size', 1)
            )
            
            # PHASE 2: Start the AI-orchestrated workflow using Bedrock Agent
            try:
                # Phase 2: Invoke Bedrock Agent asynchronously
                print(f"[SESSION] Phase 2: Invoking Bedrock Agent for session: {session_id}")
                agent_response = invoke_bedrock_agent(
                    session_id, 
                    body['client_name'], 
                    body.get('project_name', ''), 
                    body.get('industry', ''), 
                    body['requirements'], 
                    body.get('duration', ''), 
                    body.get('team_size', 1)
                )
                
                print(f"[SESSION] ✓ Bedrock Agent invocation completed for session: {session_id}")
                print(f"[SESSION] Agent response received: {json.dumps(agent_response, default=str, indent=2)}")
                
                # Update status to indicate AgentCore is processing
                dynamodb = boto3.client('dynamodb')
                dynamodb.update_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}},
                    UpdateExpression='SET #status = :status, updated_at = :ua',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'AGENTCORE_PROCESSING'},
                        ':ua': {'S': datetime.utcnow().isoformat()}
                    }
                )
                
                return create_cors_response(200, {
                    'session_id': session_id,
                    'message': 'Assessment started with AgentCore (Phase 2)',
                    'mode': 'agentcore'
                })
                
            except Exception as e:
                print(f"AgentCore invocation failed, falling back to Phase 1: {str(e)}")
                
                # FALLBACK: Use direct Lambda chain (Phase 1) if AgentCore fails
                lambda_client = boto3.client('lambda')
                lambda_client.invoke(
                    FunctionName=os.environ.get('REQUIREMENTS_ANALYZER_ARN'),
                    InvocationType='Event',
                    Payload=json.dumps({
                        'session_id': session_id,
                        'requirements': body['requirements']
                    })
                )
                
                return create_cors_response(200, {
                    'session_id': session_id,
                    'message': 'Assessment started with direct chain (Phase 1 fallback)',
                    'mode': 'fallback'
                })
            
        elif http_method == 'GET' and '/api/agent-status/' in path:
            session_id = event['pathParameters']['session_id']
            status = get_session_status(session_id)
            
            if status:
                return create_cors_response(200, status)
            else:
                return create_cors_response(404, {
                    'error': 'Session not found'
                })
                
        elif http_method == 'GET' and '/api/results/' in path:
            session_id = event['pathParameters']['session_id']
            status = get_session_status(session_id)
            
            if status and status['document_urls']:
                return create_cors_response(200, {
                    'powerpoint_url': next((url for url in status['document_urls'] if 'pptx' in url.lower()), None),
                    'sow_url': next((url for url in status['document_urls'] if 'sow' in url.lower()), None),
                    'cost_data': json.loads(status.get('cost_data', '{}'))
                })
            else:
                return create_cors_response(404, {
                    'error': 'No documents available yet'
                })
        
        elif http_method == 'POST' and path == '/api/upload-template':
            # Handle template upload
            if 'file' not in event['multiValueHeaders']:
                return create_cors_response(400, {
                    'error': 'No file provided'
                })
                
            # Process file upload using S3
            s3 = boto3.client('s3')
            file_content = event['body']
            file_name = event['multiValueHeaders']['file'][0]
            
            # Upload to templates bucket
            s3.put_object(
                Bucket=os.environ['TEMPLATES_BUCKET_NAME'],
                Key=f'templates/{file_name}',
                Body=file_content
            )
            
            return create_cors_response(200, {
                'message': 'Template uploaded successfully',
                'template_path': f'templates/{file_name}'
            })
        
        return create_cors_response(404, {
            'error': 'Route not found'
        })
        
    except Exception as e:
        return create_cors_response(500, {
            'error': str(e)
        })