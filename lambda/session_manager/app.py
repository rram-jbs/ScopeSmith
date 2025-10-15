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

def invoke_agentcore_runtime(session_id, client_name, project_name, industry, requirements, duration, team_size):
    """Invoke AgentCore Runtime for autonomous proposal generation"""
    print(f"[AGENTCORE RUNTIME] Starting invocation for session: {session_id}")
    
    runtime_arn = os.environ.get('AGENTCORE_RUNTIME_ARN')
    runtime_id = os.environ.get('AGENTCORE_RUNTIME_ID')
    
    if not runtime_arn or not runtime_id:
        raise ValueError("AgentCore Runtime not configured. Please run setup-agentcore.py script.")
    
    print(f"[AGENTCORE RUNTIME] Runtime ARN: {runtime_arn}")
    print(f"[AGENTCORE RUNTIME] Runtime ID: {runtime_id}")
    
    bedrock_agentcore_runtime = boto3.client('bedrock-agentcore-runtime')
    
    # Create input payload for runtime
    input_payload = {
        'prompt': f"""Convert the following client meeting notes into a complete project proposal:

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
    }
    
    print(f"[AGENTCORE RUNTIME] Sending payload to runtime")
    
    response = bedrock_agentcore_runtime.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(input_payload).encode()
    )
    
    print(f"[AGENTCORE RUNTIME] Runtime invocation successful")
    
    # Process streaming response
    content = []
    if "text/event-stream" in response.get("contentType", ""):
        for line in response["response"].iter_lines(chunk_size=10):
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]
                    print(f"[RUNTIME STREAM] {line}")
                    content.append(line)
    
    full_response = "\n".join(content)
    
    return {
        'status': 'completed',
        'response': full_response,
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
                print(f"[SESSION] Invoking AgentCore Runtime for session: {session_id}")
                agent_response = invoke_agentcore_runtime(
                    session_id, 
                    body['client_name'], 
                    body.get('project_name', ''), 
                    body.get('industry', ''), 
                    body['requirements'], 
                    body.get('duration', ''), 
                    body.get('team_size', 1)
                )
                
                print(f"[SESSION] ✓ AgentCore Runtime invocation completed")
                
                # Update status
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
                    'message': 'Assessment started with AgentCore Runtime'
                })
                
            except Exception as e:
                print(f"[SESSION] ✗ AgentCore Runtime invocation failed: {str(e)}")
                
                # Update session with error
                dynamodb = boto3.client('dynamodb')
                dynamodb.update_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}},
                    UpdateExpression='SET #status = :status, error_message = :error, updated_at = :ua',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'ERROR'},
                        ':error': {'S': f'AgentCore Runtime invocation failed: {str(e)}'},
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