import os
import json
import boto3
import uuid
import time
from datetime import datetime
from botocore.exceptions import ClientError

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

def create_session(client_name, project_name, industry, requirements, duration, team_size):
    """Create a new session record in DynamoDB with PENDING status"""
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    dynamodb = boto3.client('dynamodb')
    dynamodb.put_item(
        TableName=os.environ['SESSIONS_TABLE_NAME'],
        Item={
            'session_id': {'S': session_id},
            'status': {'S': 'PENDING'},  # Initial status
            'client_name': {'S': client_name},
            'project_name': {'S': project_name},
            'industry': {'S': industry},
            'duration': {'S': duration},
            'team_size': {'N': str(team_size)},
            'requirements_data': {'S': json.dumps({
                'raw_requirements': requirements
            })},
            'current_stage': {'S': 'Initializing'},
            'progress': {'N': '0'},
            'created_at': {'S': timestamp},
            'updated_at': {'S': timestamp}
        }
    )
    
    print(f"[SESSION] Created session {session_id} with PENDING status")
    return session_id

def invoke_agent_async(session_id, client_name, project_name, industry, requirements, duration, team_size):
    """
    Invoke the Bedrock Agent processing asynchronously using Lambda self-invocation.
    This allows the API to return immediately while processing continues in the background.
    """
    try:
        lambda_client = boto3.client('lambda')
        
        # Prepare payload for async invocation
        payload = {
            'action': 'PROCESS_AGENT_WORKFLOW',
            'session_id': session_id,
            'client_name': client_name,
            'project_name': project_name,
            'industry': industry,
            'requirements': requirements,
            'duration': duration,
            'team_size': team_size
        }
        
        # Invoke this Lambda function asynchronously to process the agent workflow
        function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        
        print(f"[SESSION] Invoking async workflow for session {session_id}")
        
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(payload)
        )
        
        print(f"[SESSION] Async invocation submitted successfully")
        return True
        
    except Exception as e:
        print(f"[SESSION] ERROR: Failed to invoke async workflow: {str(e)}")
        
        # Update session with error
        dynamodb = boto3.client('dynamodb')
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET #status = :status, error_message = :error, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'ERROR'},
                ':error': {'S': f'Failed to start async workflow: {str(e)}'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        raise e

def update_session_status(session_id, status, stage=None, progress=None, error_message=None):
    """Helper function to update session status in DynamoDB"""
    dynamodb = boto3.client('dynamodb')
    
    update_expression_parts = ['#status = :status', 'updated_at = :ua']
    expression_attribute_names = {'#status': 'status'}
    expression_attribute_values = {
        ':status': {'S': status},
        ':ua': {'S': datetime.utcnow().isoformat()}
    }
    
    if stage:
        update_expression_parts.append('current_stage = :stage')
        expression_attribute_values[':stage'] = {'S': stage}
    
    if progress is not None:
        update_expression_parts.append('progress = :progress')
        expression_attribute_values[':progress'] = {'N': str(progress)}
    
    if error_message:
        update_expression_parts.append('error_message = :error')
        expression_attribute_values[':error'] = {'S': error_message}
    
    dynamodb.update_item(
        TableName=os.environ['SESSIONS_TABLE_NAME'],
        Key={'session_id': {'S': session_id}},
        UpdateExpression='SET ' + ', '.join(update_expression_parts),
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values
    )

def invoke_bedrock_agent(session_id, client_name, project_name, industry, requirements, duration, team_size):
    """
    Invoke Bedrock Agent with retry logic and proper status tracking.
    This runs asynchronously after the API has already returned a session ID.
    """
    print(f"[BEDROCK AGENT] Starting invocation for session: {session_id}")
    
    agent_id = os.environ.get('BEDROCK_AGENT_ID')
    agent_alias_id = os.environ.get('BEDROCK_AGENT_ALIAS_ID')
    
    if not agent_id or not agent_alias_id:
        raise ValueError("Bedrock Agent not configured. Please run setup-agentcore.py script.")
    
    if agent_id == 'PLACEHOLDER_AGENT_ID' or agent_alias_id == 'PLACEHOLDER_ALIAS_ID':
        raise ValueError("Bedrock Agent placeholders detected. Please run setup-agentcore.py to configure actual agent.")
    
    print(f"[BEDROCK AGENT] Agent ID: {agent_id}")
    print(f"[BEDROCK AGENT] Agent Alias ID: {agent_alias_id}")
    
    # Update status to PROCESSING
    update_session_status(session_id, 'PROCESSING', stage='Starting agent workflow', progress=5)
    
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
            update_session_status(session_id, 'PROCESSING', stage='Agent workflow started', progress=10)
            break  # Success, exit retry loop
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"[BEDROCK AGENT] ⚠ Throttled, waiting {wait_time}s before retry...")
                update_session_status(session_id, 'PROCESSING', stage=f'Retrying (throttled, attempt {attempt + 2})')
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
    
    # Progress tracking based on expected workflow stages
    stage_progress = {
        'RequirementsAnalyzer': 30,
        'CostCalculator': 50,
        'TemplateRetriever': 60,
        'PowerPointGenerator': 80,
        'SOWGenerator': 95
    }
    
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
                                    ':events': {'S': json.dumps(agent_events, cls=DateTimeEncoder)},
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
                        
                        # Update progress based on stage
                        progress = stage_progress.get(action_group_name, 15 + (action_group_invocations * 10))
                        update_session_status(session_id, 'PROCESSING', stage=f'Running {action_group_name}', progress=progress)
                        
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
                                        ':events': {'S': json.dumps(agent_events, cls=DateTimeEncoder)},
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
                            print(f"[FINAL RESPONSE] {json.dumps(final_resp, indent=2, cls=DateTimeEncoder)}")
                            
                            agent_events.append({
                                'type': 'final_response',
                                'timestamp': datetime.utcnow().isoformat(),
                                'content': json.dumps(final_resp, cls=DateTimeEncoder)
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
    
    except Exception as stream_error:
        print(f"[BEDROCK AGENT] ✗ Error processing event stream: {str(stream_error)}")
        
        update_session_status(
            session_id, 
            'ERROR', 
            stage='Agent workflow failed', 
            error_message=str(stream_error)
        )
        
        try:
            dynamodb.update_item(
                TableName=os.environ['SESSIONS_TABLE_NAME'],
                Key={'session_id': {'S': session_id}},
                UpdateExpression='SET agent_events = :events, updated_at = :ua',
                ExpressionAttributeValues={
                    ':events': {'S': json.dumps(agent_events, cls=DateTimeEncoder)},
                    ':ua': {'S': datetime.utcnow().isoformat()}
                }
            )
        except:
            pass
        
        raise stream_error
    
    # Final update - workflow completed
    try:
        # Check if documents were actually generated by querying DynamoDB
        dynamodb = boto3.client('dynamodb')
        session_check = dynamodb.get_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}}
        )
        
        document_urls = session_check.get('Item', {}).get('document_urls', {}).get('L', [])
        
        # Only mark as COMPLETED if we have document URLs
        if len(document_urls) > 0:
            print(f"[BEDROCK AGENT] ✓ Documents generated: {len(document_urls)} files")
            update_session_status(session_id, 'COMPLETED', stage='Workflow completed', progress=100)
            
            dynamodb.update_item(
                TableName=os.environ['SESSIONS_TABLE_NAME'],
                Key={'session_id': {'S': session_id}},
                UpdateExpression='SET agent_events = :events, agent_response = :ar, updated_at = :ua',
                ExpressionAttributeValues={
                    ':events': {'S': json.dumps(agent_events, cls=DateTimeEncoder)},
                    ':ar': {'S': json.dumps({
                        'response': full_response,
                        'tool_calls': tool_calls,
                        'action_group_invocations': action_group_invocations
                    }, cls=DateTimeEncoder)},
                    ':ua': {'S': datetime.utcnow().isoformat()}
                }
            )
        else:
            print(f"[BEDROCK AGENT] ✗ No documents were generated")
            update_session_status(
                session_id, 
                'ERROR', 
                stage='Document generation failed', 
                error_message='Agent workflow completed but no documents were generated. Please check the PowerPoint and SOW generator logs.'
            )
            
            dynamodb.update_item(
                TableName=os.environ['SESSIONS_TABLE_NAME'],
                Key={'session_id': {'S': session_id}},
                UpdateExpression='SET agent_events = :events, agent_response = :ar, updated_at = :ua',
                ExpressionAttributeValues={
                    ':events': {'S': json.dumps(agent_events, cls=DateTimeEncoder)},
                    ':ar': {'S': json.dumps({
                        'response': full_response,
                        'tool_calls': tool_calls,
                        'action_group_invocations': action_group_invocations,
                        'error': 'No documents generated'
                    }, cls=DateTimeEncoder)},
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

def get_session_status(session_id):
    """Get current session status from DynamoDB"""
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.get_item(
        TableName=os.environ['SESSIONS_TABLE_NAME'],
        Key={'session_id': {'S': session_id}}
    )
    
    if 'Item' not in response:
        return None
        
    item = response['Item']
    
    # Calculate progress percentage if not explicitly set
    progress = int(item.get('progress', {}).get('N', '0'))
    
    return {
        'session_id': item['session_id']['S'],
        'status': item['status']['S'],
        'current_stage': item.get('current_stage', {}).get('S', ''),
        'progress': progress,
        'client_name': item['client_name']['S'],
        'project_name': item['project_name']['S'],
        'industry': item['industry']['S'],
        'duration': item['duration']['S'],
        'team_size': int(item['team_size']['N']),
        'requirements_data': json.loads(item.get('requirements_data', {}).get('S', '{}')),
        'cost_data': json.loads(item.get('cost_data', {}).get('S', '{}')),
        'agent_events': item.get('agent_events', {}).get('S', '[]'),
        'template_paths': [p['S'] for p in item.get('template_paths', {}).get('L', [])],
        'document_urls': [url['S'] for url in item.get('document_urls', {}).get('L', [])],
        'error_message': item.get('error_message', {}).get('S', None),
        'created_at': item['created_at']['S'],
        'updated_at': item['updated_at']['S']
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
        'body': json.dumps(body, cls=DateTimeEncoder) if isinstance(body, dict) else body
    }

def handler(event, context):
    """
    Main handler for Session Manager Lambda.
    
    Handles two types of invocations:
    1. API Gateway requests (HTTP events) - Create session and return immediately
    2. Async self-invocations (direct Lambda events) - Process agent workflow in background
    """
    try:
        # Check if this is an async workflow invocation (not from API Gateway)
        if 'action' in event and event['action'] == 'PROCESS_AGENT_WORKFLOW':
            print(f"[SESSION] Processing async agent workflow")
            
            session_id = event['session_id']
            
            try:
                # Run the agent workflow (this can take 3-5 minutes)
                agent_response = invoke_bedrock_agent(
                    session_id,
                    event['client_name'],
                    event['project_name'],
                    event['industry'],
                    event['requirements'],
                    event['duration'],
                    event['team_size']
                )
                
                print(f"[SESSION] ✓ Agent workflow completed for session: {session_id}")
                print(f"[SESSION] Tool calls made: {agent_response.get('action_group_invocations', 0)}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Agent workflow completed',
                        'session_id': session_id
                    })
                }
                
            except ValueError as ve:
                print(f"[SESSION] ✗ Configuration error: {str(ve)}")
                update_session_status(
                    session_id, 
                    'ERROR', 
                    stage='Configuration error',
                    error_message=str(ve)
                )
                
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Configuration error',
                        'details': str(ve)
                    })
                }
                
            except Exception as e:
                print(f"[SESSION] ✗ Agent workflow failed: {str(e)}")
                import traceback
                print(f"[SESSION] Traceback: {traceback.format_exc()}")
                
                update_session_status(
                    session_id,
                    'ERROR',
                    stage='Agent workflow error',
                    error_message=str(e)
                )
                
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Agent workflow failed',
                        'details': str(e)
                    })
                }
        
        # Handle API Gateway HTTP requests
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
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
            
            # Create session immediately
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
            
            # Invoke agent workflow asynchronously
            try:
                invoke_agent_async(
                    session_id,
                    body['client_name'],
                    body.get('project_name', ''),
                    body.get('industry', ''),
                    body['requirements'],
                    body.get('duration', ''),
                    body.get('team_size', 1)
                )
                
                # Return immediately with session ID and pending status
                return create_cors_response(200, {
                    'session_id': session_id,
                    'status': 'PENDING',
                    'message': 'Assessment request received. Processing in background.',
                    'poll_url': f'/api/agent-status/{session_id}'
                })
                
            except Exception as e:
                print(f"[SESSION] ✗ Failed to start async workflow: {str(e)}")
                return create_cors_response(500, {
                    'session_id': session_id,
                    'error': 'Failed to start workflow',
                    'details': str(e)
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
        import traceback
        print(f"[SESSION] Traceback: {traceback.format_exc()}")
        return create_cors_response(500, {
            'error': str(e)
        })