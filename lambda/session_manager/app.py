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
    """Invoke Bedrock Agent for autonomous proposal generation"""
    print(f"[BEDROCK AGENT] Starting invocation for session: {session_id}")
    
    agent_id = os.environ.get('BEDROCK_AGENT_ID')
    agent_alias_id = os.environ.get('BEDROCK_AGENT_ALIAS_ID')
    
    if not agent_id or not agent_alias_id:
        raise ValueError("Bedrock Agent not configured. Please run setup-agentcore.py script.")
    
    print(f"[BEDROCK AGENT] Agent ID: {agent_id}")
    print(f"[BEDROCK AGENT] Agent Alias ID: {agent_alias_id}")
    
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
    
    # Create input text for agent
    input_text = f"""Convert the following client meeting notes into a complete project proposal:

Client Information:
- Client Name: {client_name}
- Project Name: {project_name}
- Industry: {industry}
- Project Duration: {duration}
- Team Size: {team_size}

Meeting Notes:
{requirements}

Session ID: {session_id}

Please work autonomously to complete the full proposal workflow."""

    print(f"[BEDROCK AGENT] Sending input to agent")
    
    response = bedrock_agent_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        inputText=input_text
    )
    
    print(f"[BEDROCK AGENT] Agent invocation successful")
    
    # Process the EventStream
    event_stream = response['completion']
    full_response = ""
    tool_calls = []
    
    print(f"[BEDROCK AGENT] Processing EventStream...")
    
    for event in event_stream:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                chunk_text = chunk['bytes'].decode('utf-8')
                print(f"[CHUNK] {chunk_text}")
                full_response += chunk_text
        
        elif 'trace' in event:
            trace = event['trace']
            print(f"[TRACE] {json.dumps(trace, default=str, indent=2)}")
            
            # Track tool invocations
            if 'trace' in trace:
                trace_data = trace['trace']
                if 'orchestrationTrace' in trace_data:
                    orch = trace_data['orchestrationTrace']
                    if 'invocationInput' in orch:
                        tool_calls.append(orch['invocationInput'])
                        print(f"[TOOL CALL] {json.dumps(orch['invocationInput'], default=str, indent=2)}")
                    if 'observation' in orch:
                        print(f"[TOOL RESPONSE] {json.dumps(orch['observation'], default=str, indent=2)}")
        
        elif 'returnControl' in event:
            print(f"[RETURN_CONTROL] Agent requires user input")
            return {
                'status': 'awaiting_input',
                'event': event['returnControl'],
                'session_id': session_id
            }
    
    print(f"[BEDROCK AGENT] EventStream processing complete")
    print(f"[BEDROCK AGENT] Full response length: {len(full_response)} chars")
    print(f"[BEDROCK AGENT] Total tool calls: {len(tool_calls)}")
    
    return {
        'status': 'completed',
        'response': full_response,
        'tool_calls': tool_calls,
        'session_id': session_id
    }

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
            
            try:
                print(f"[SESSION] Invoking Bedrock Agent for session: {session_id}")
                agent_response = invoke_bedrock_agent(
                    session_id, 
                    body['client_name'], 
                    body.get('project_name', ''), 
                    body.get('industry', ''), 
                    body['requirements'], 
                    body.get('duration', ''), 
                    body.get('team_size', 1)
                )
                
                print(f"[SESSION] ✓ Bedrock Agent invocation completed")
                
                # Update status
                dynamodb = boto3.client('dynamodb')
                dynamodb.update_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}},
                    UpdateExpression='SET #status = :status, updated_at = :ua',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'AGENT_PROCESSING'},
                        ':ua': {'S': datetime.utcnow().isoformat()}
                    }
                )
                
                return create_cors_response(200, {
                    'session_id': session_id,
                    'message': 'Assessment started with Bedrock Agent'
                })
                
            except Exception as e:
                print(f"[SESSION] ✗ Bedrock Agent invocation failed: {str(e)}")
                
                # Update session with error
                dynamodb = boto3.client('dynamodb')
                dynamodb.update_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}},
                    UpdateExpression='SET #status = :status, error_message = :error, updated_at = :ua',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'ERROR'},
                        ':error': {'S': f'Bedrock Agent invocation failed: {str(e)}'},
                        ':ua': {'S': datetime.utcnow().isoformat()}
                    }
                )
                
                return create_cors_response(500, {
                    'session_id': session_id,
                    'error': str(e)
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
                    'cost_data': status.get('cost_data', {})
                })
            else:
                return create_cors_response(404, {
                    'error': 'No documents available yet'
                })
        
        elif http_method == 'POST' and path == '/api/upload-template':
            # Handle template upload
            if 'file' not in event.get('multiValueHeaders', {}):
                return create_cors_response(400, {
                    'error': 'No file provided'
                })
                
            s3 = boto3.client('s3')
            file_content = event['body']
            file_name = event['multiValueHeaders']['file'][0]
            
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
        print(f"[SESSION] ✗ Unexpected error: {str(e)}")
        return create_cors_response(500, {
            'error': str(e)
        })