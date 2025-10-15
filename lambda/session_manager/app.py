import os
import json
import boto3
import uuid
import time
from datetime import datetime
from botocore.exceptions import ClientError

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
        'agent_events': item.get('agent_events', {}).get('S', '[]'),  # Add agent events
        'current_stage': item.get('current_stage', {}).get('S', ''),
        'template_paths': [p['S'] for p in item.get('template_paths', {}).get('L', [])],
        'document_urls': [url['S'] for url in item.get('document_urls', {}).get('L', [])],
        'error_message': item.get('error_message', {}).get('S', None),
        'created_at': item['created_at']['S'],
        'updated_at': item['updated_at']['S']
    }

def invoke_bedrock_agent(session_id, client_name, project_name, industry, requirements, duration, team_size):
    """Invoke Bedrock Agent with retry logic for throttling"""
    print(f"[BEDROCK AGENT] Starting invocation for session: {session_id}")
    
    agent_id = os.environ.get('BEDROCK_AGENT_ID')
    agent_alias_id = os.environ.get('BEDROCK_AGENT_ALIAS_ID')
    
    if not agent_id or not agent_alias_id:
        raise ValueError("Bedrock Agent not configured. Please run setup-agentcore.py script.")
    
    if agent_id == 'PLACEHOLDER_AGENT_ID' or agent_alias_id == 'PLACEHOLDER_ALIAS_ID':
        raise ValueError("Bedrock Agent placeholders detected. Please run setup-agentcore.py to configure actual agent.")
    
    print(f"[BEDROCK AGENT] Agent ID: {agent_id}")
    print(f"[BEDROCK AGENT] Agent Alias ID: {agent_alias_id}")
    
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
    dynamodb = boto3.client('dynamodb')
    
    # Create input text for agent with clear instructions
    input_text = f"""I need you to generate a complete project proposal for the following client:

Client Information:
- Client Name: {client_name}
- Project Name: {project_name}
- Industry: {industry}
- Desired Duration: {duration}
- Team Size: {team_size}

Meeting Notes/Requirements:
{requirements}

Session ID: {session_id}

Please execute the following workflow:
1. Analyze the requirements using the analyze_requirements function
2. Calculate project costs using the calculate_project_cost function
3. Retrieve appropriate templates using the retrieve_templates function
4. Generate a PowerPoint presentation using the generate_powerpoint function
5. Generate a Statement of Work document using the generate_sow function

Work autonomously through all steps and provide me with the final document URLs."""

    print(f"[BEDROCK AGENT] Input text length: {len(input_text)} characters")
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"[BEDROCK AGENT] Invoking agent (attempt {attempt + 1}/{max_retries})...")
            
            response = bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=True
            )
            
            print(f"[BEDROCK AGENT] ✓ Agent invoked successfully")
            break  # Success, exit retry loop
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"[BEDROCK AGENT] ⚠ Throttled, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            else:
                print(f"[BEDROCK AGENT] ✗ Failed to invoke agent: {str(e)}")
                raise e
    
    # Process the EventStream with throttling handling
    event_stream = response.get('completion')
    if not event_stream:
        print(f"[BEDROCK AGENT] ✗ No completion event stream in response")
        raise ValueError("No completion event stream received from agent")
    
    full_response = ""
    tool_calls = []
    action_group_invocations = 0
    chunks_received = 0
    agent_events = []
    last_update_time = time.time()
    update_interval = 1.0  # Update DynamoDB at most once per second to avoid throttling
    
    print(f"[BEDROCK AGENT] Processing EventStream...")
    
    try:
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    chunks_received += 1
                    print(f"[CHUNK #{chunks_received}] {chunk_text[:200]}{'...' if len(chunk_text) > 200 else ''}")
                    full_response += chunk_text
                    
                    agent_events.append({
                        'type': 'chunk',
                        'timestamp': datetime.utcnow().isoformat(),
                        'content': chunk_text
                    })
                    
                    # Batch update to reduce DynamoDB write frequency
                    if time.time() - last_update_time > update_interval:
                        try:
                            dynamodb.update_item(
                                TableName=os.environ['SESSIONS_TABLE_NAME'],
                                Key={'session_id': {'S': session_id}},
                                UpdateExpression='SET agent_events = :events, updated_at = :ua',
                                ExpressionAttributeValues={
                                    ':events': {'S': json.dumps(agent_events)},
                                    ':ua': {'S': datetime.utcnow().isoformat()}
                                }
                            )
                            last_update_time = time.time()
                        except ClientError as db_error:
                            print(f"[BEDROCK AGENT] ⚠ DynamoDB update failed: {db_error}")
            
            elif 'trace' in event:
                trace = event['trace']
                trace_obj = trace.get('trace', {})
                
                if 'orchestrationTrace' in trace_obj:
                    orch_trace = trace_obj['orchestrationTrace']
                    
                    if 'invocationInput' in orch_trace:
                        invocation_input = orch_trace['invocationInput']
                        action_group_invocations += 1
                        
                        action_group_name = invocation_input.get('actionGroupInvocationInput', {}).get('actionGroupName', 'Unknown')
                        function_name = invocation_input.get('actionGroupInvocationInput', {}).get('function', 'Unknown')
                        parameters = invocation_input.get('actionGroupInvocationInput', {}).get('parameters', [])
                        
                        print(f"[TOOL CALL #{action_group_invocations}] Action Group: {action_group_name}")
                        
                        tool_call_event = {
                            'type': 'tool_call',
                            'timestamp': datetime.utcnow().isoformat(),
                            'action_group': action_group_name,
                            'function': function_name,
                            'parameters': parameters
                        }
                        
                        agent_events.append(tool_call_event)
                        tool_calls.append(tool_call_event)
                        
                        # Update with rate limiting
                        if time.time() - last_update_time > update_interval:
                            try:
                                dynamodb.update_item(
                                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                                    Key={'session_id': {'S': session_id}},
                                    UpdateExpression='SET agent_events = :events, current_stage = :stage, updated_at = :ua',
                                    ExpressionAttributeValues={
                                        ':events': {'S': json.dumps(agent_events)},
                                        ':stage': {'S': action_group_name},
                                        ':ua': {'S': datetime.utcnow().isoformat()}
                                    }
                                )
                                last_update_time = time.time()
                            except ClientError as db_error:
                                print(f"[BEDROCK AGENT] ⚠ DynamoDB update failed: {db_error}")
                    
                    if 'observation' in orch_trace:
                        observation = orch_trace['observation']
                        
                        if 'actionGroupInvocationOutput' in observation:
                            output = observation['actionGroupInvocationOutput']
                            response_text = output.get('text', '')
                            print(f"[TOOL RESPONSE] {response_text[:300]}{'...' if len(response_text) > 300 else ''}")
                            
                            agent_events.append({
                                'type': 'tool_response',
                                'timestamp': datetime.utcnow().isoformat(),
                                'content': response_text
                            })
                        
                        if 'finalResponse' in observation:
                            final_resp = observation['finalResponse']
                            print(f"[FINAL RESPONSE] {json.dumps(final_resp, indent=2)}")
                            
                            agent_events.append({
                                'type': 'final_response',
                                'timestamp': datetime.utcnow().isoformat(),
                                'content': json.dumps(final_resp)
                            })
                    
                    if 'rationale' in orch_trace:
                        rationale = orch_trace['rationale']
                        reasoning_text = rationale.get('text', '')
                        print(f"[AGENT REASONING] {reasoning_text}")
                        
                        agent_events.append({
                            'type': 'reasoning',
                            'timestamp': datetime.utcnow().isoformat(),
                            'content': reasoning_text
                        })
            
            elif 'throttlingException' in event:
                print(f"[BEDROCK AGENT] ⚠ Throttled during event stream processing")
                agent_events.append({
                    'type': 'warning',
                    'timestamp': datetime.utcnow().isoformat(),
                    'content': 'Rate limit reached, slowing down...'
                })
                time.sleep(2)  # Brief pause before continuing
                continue
            
            elif 'internalServerException' in event:
                error = event['internalServerException']
                print(f"[ERROR] Internal server error: {error}")
                raise Exception(f"Bedrock agent internal error: {error}")
            
            elif 'validationException' in event:
                error = event['validationException']
                print(f"[ERROR] Validation error: {error}")
                raise Exception(f"Bedrock agent validation error: {error}")
            
            elif 'throttlingException' in event:
                error = event['throttlingException']
                print(f"[ERROR] Throttling error: {error}")
                raise Exception(f"Bedrock agent throttling error: {error}")
    
    except Exception as stream_error:
        print(f"[BEDROCK AGENT] ✗ Error processing event stream: {str(stream_error)}")
        
        try:
            dynamodb.update_item(
                TableName=os.environ['SESSIONS_TABLE_NAME'],
                Key={'session_id': {'S': session_id}},
                UpdateExpression='SET #status = :status, error_message = :error, agent_events = :events, updated_at = :ua',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': 'ERROR'},
                    ':error': {'S': str(stream_error)},
                    ':events': {'S': json.dumps(agent_events)},
                    ':ua': {'S': datetime.utcnow().isoformat()}
                }
            )
        except:
            pass
        
        raise stream_error
    
    try:
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET agent_events = :events, #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':events': {'S': json.dumps(agent_events)},
                ':status': {'S': 'COMPLETED'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
    except ClientError as db_error:
        print(f"[BEDROCK AGENT] ⚠ Final DynamoDB update failed: {db_error}")
    
    print(f"[BEDROCK AGENT] ✓ EventStream processing complete")
    
    return {
        'status': 'completed',
        'response': full_response,
        'tool_calls': tool_calls,
        'action_group_invocations': action_group_invocations,
        'chunks_received': chunks_received,
        'session_id': session_id,
        'agent_events': agent_events
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
            
            # Validate required fields
            if 'client_name' not in body or 'requirements' not in body:
                return create_cors_response(400, {
                    'error': 'Missing required fields: client_name and requirements'
                })
            
            session_id = create_session(
                client_name=body['client_name'],
                project_name=body.get('project_name', ''),
                industry=body.get('industry', ''),
                requirements=body['requirements'],
                duration=body.get('duration', ''),
                team_size=body.get('team_size', 1)
            )
            
            print(f"[SESSION] Created session: {session_id}")
            print(f"[SESSION] Client: {body['client_name']}")
            print(f"[SESSION] Requirements length: {len(body['requirements'])} characters")
            
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
                print(f"[SESSION] Response status: {agent_response.get('status')}")
                print(f"[SESSION] Tool calls made: {agent_response.get('action_group_invocations', 0)}")
                print(f"[SESSION] Response chunks: {agent_response.get('chunks_received', 0)}")
                
                # Update status based on agent response
                dynamodb = boto3.client('dynamodb')
                
                if agent_response.get('status') == 'completed':
                    status_value = 'AGENT_PROCESSING'
                elif agent_response.get('status') == 'awaiting_input':
                    status_value = 'AWAITING_INPUT'
                else:
                    status_value = 'AGENT_PROCESSING'
                
                dynamodb.update_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}},
                    UpdateExpression='SET #status = :status, agent_response = :ar, updated_at = :ua',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': status_value},
                        ':ar': {'S': json.dumps({
                            'response': agent_response.get('response', ''),
                            'tool_calls': agent_response.get('tool_calls', []),
                            'action_group_invocations': agent_response.get('action_group_invocations', 0)
                        })},
                        ':ua': {'S': datetime.utcnow().isoformat()}
                    }
                )
                
                return create_cors_response(200, {
                    'session_id': session_id,
                    'message': 'Assessment started with Bedrock Agent',
                    'status': agent_response.get('status'),
                    'tool_calls': agent_response.get('action_group_invocations', 0)
                })
                
            except ValueError as ve:
                print(f"[SESSION] ✗ Configuration error: {str(ve)}")
                
                # Update session with configuration error
                dynamodb = boto3.client('dynamodb')
                dynamodb.update_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}},
                    UpdateExpression='SET #status = :status, error_message = :error, updated_at = :ua',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'CONFIGURATION_ERROR'},
                        ':error': {'S': str(ve)},
                        ':ua': {'S': datetime.utcnow().isoformat()}
                    }
                )
                
                return create_cors_response(500, {
                    'session_id': session_id,
                    'error': 'Agent configuration error. Please run setup script.',
                    'details': str(ve)
                })
                
            except Exception as e:
                print(f"[SESSION] ✗ Bedrock Agent invocation failed: {str(e)}")
                import traceback
                print(f"[SESSION] Traceback: {traceback.format_exc()}")
                
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
            session_id = path.split('/')[-1]  # Extract session_id from path
            status = get_session_status(session_id)
            
            if status:
                return create_cors_response(200, status)
            else:
                return create_cors_response(404, {
                    'error': 'Session not found'
                })
                
        elif http_method == 'GET' and '/api/results/' in path:
            session_id = path.split('/')[-1]  # Extract session_id from path
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