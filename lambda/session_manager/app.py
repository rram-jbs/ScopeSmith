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

def handler(event, context):
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        if http_method == 'POST' and path == '/api/submit-assessment':
            body = json.loads(event['body'])
            session_id = create_session(
                client_name=body['client_name'],
                project_name=body['project_name'],
                industry=body['industry'],
                requirements=body['requirements'],
                duration=body['duration'],
                team_size=body['team_size']
            )
            
            # Start the workflow by invoking the requirements analyzer
            lambda_client = boto3.client('lambda')
            lambda_client.invoke(
                FunctionName=os.environ.get('REQUIREMENTS_ANALYZER_ARN'),
                InvocationType='Event',
                Payload=json.dumps({
                    'session_id': session_id,
                    'requirements': body['requirements']
                })
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'session_id': session_id,
                    'message': 'Assessment started'
                })
            }
            
        elif http_method == 'GET' and '/api/agent-status/' in path:
            session_id = event['pathParameters']['session_id']
            status = get_session_status(session_id)
            
            if status:
                return {
                    'statusCode': 200,
                    'body': json.dumps(status)
                }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'Session not found'
                    })
                }
                
        elif http_method == 'GET' and '/api/results/' in path:
            session_id = event['pathParameters']['session_id']
            status = get_session_status(session_id)
            
            if status and status['document_urls']:
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'powerpoint_url': next((url for url in status['document_urls'] if 'pptx' in url.lower()), None),
                        'sow_url': next((url for url in status['document_urls'] if 'sow' in url.lower()), None),
                        'cost_data': json.loads(status.get('cost_data', '{}'))
                    })
                }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'No documents available yet'
                    })
                }
        
        elif http_method == 'POST' and path == '/api/upload-template':
            # Handle template upload
            if 'file' not in event['multiValueHeaders']:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'No file provided'
                    })
                }
                
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
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Template uploaded successfully',
                    'template_path': f'templates/{file_name}'
                })
            }
        
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Route not found'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }