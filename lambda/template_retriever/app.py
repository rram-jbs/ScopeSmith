import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    """
    AgentCore Action Group Function for Template Retrieval
    This function is invoked by the Bedrock Agent to retrieve appropriate templates
    """
    try:
        print(f"[TEMPLATE RETRIEVER] Received event: {json.dumps(event)}")
        
        # Check if this is a Bedrock Agent action group invocation
        if 'agent' in event or 'actionGroup' in event or 'function' in event:
            print(f"[TEMPLATE RETRIEVER] Bedrock Agent action group invocation detected")
            
            parameters = event.get('parameters', [])
            param_dict = {}
            for param in parameters:
                param_dict[param['name']] = param['value']
            
            session_id = param_dict.get('session_id')
            template_type = param_dict.get('template_type', 'both')
        elif 'inputText' in event:
            try:
                params = json.loads(event['inputText'])
                session_id = params['session_id']
                template_type = params.get('template_type', 'both')
            except (json.JSONDecodeError, KeyError) as e:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Invalid input format from AgentCore: {str(e)}'
                    })
                }
        else:
            session_id = event.get('session_id')
            template_type = event.get('template_type', 'both')

        if not session_id:
            return format_agent_response(400, 'Missing required parameter: session_id')

        print(f"[TEMPLATE RETRIEVER] Starting template retrieval for session: {session_id}")
        print(f"[TEMPLATE RETRIEVER] Template type requested: {template_type}")
        
        # Initialize AWS clients
        dynamodb = boto3.client('dynamodb')
        s3 = boto3.client('s3')
        
        # Update status to retrieving templates
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'RETRIEVING_TEMPLATES'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Get session data to understand project requirements
        response = dynamodb.get_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}}
        )
        
        if 'Item' not in response:
            raise ValueError(f"Session {session_id} not found")
        
        session_data = response['Item']
        requirements_data_str = session_data.get('requirements_data', {}).get('S', '{}')
        cost_data_str = session_data.get('cost_data', {}).get('S', '{}')
        
        try:
            requirements_data = json.loads(requirements_data_str)
            cost_data = json.loads(cost_data_str)
        except json.JSONDecodeError:
            requirements_data = {}
            cost_data = {}
        
        # Get available templates from S3
        template_bucket = os.environ.get('TEMPLATE_BUCKET_NAME')
        templates = {}
        
        if template_type in ['sow', 'both']:
            try:
                # List SOW templates
                sow_response = s3.list_objects_v2(
                    Bucket=template_bucket,
                    Prefix='sow-templates/'
                )
                
                sow_templates = []
                if 'Contents' in sow_response:
                    for obj in sow_response['Contents']:
                        if obj['Key'].endswith('.docx'):
                            template_name = obj['Key'].split('/')[-1].replace('.docx', '')
                            sow_templates.append({
                                'name': template_name,
                                'key': obj['Key'],
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat()
                            })
                
                templates['sow'] = sow_templates
            except Exception as e:
                templates['sow'] = []
                print(f"Error retrieving SOW templates: {e}")
        
        if template_type in ['powerpoint', 'both']:
            try:
                # List PowerPoint templates
                ppt_response = s3.list_objects_v2(
                    Bucket=template_bucket,
                    Prefix='powerpoint-templates/'
                )
                
                ppt_templates = []
                if 'Contents' in ppt_response:
                    for obj in ppt_response['Contents']:
                        if obj['Key'].endswith('.pptx'):
                            template_name = obj['Key'].split('/')[-1].replace('.pptx', '')
                            ppt_templates.append({
                                'name': template_name,
                                'key': obj['Key'],
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat()
                            })
                
                templates['powerpoint'] = ppt_templates
            except Exception as e:
                templates['powerpoint'] = []
                print(f"Error retrieving PowerPoint templates: {e}")
        
        # Select most appropriate templates based on project characteristics
        selected_templates = select_best_templates(templates, requirements_data, cost_data)
        
        # Update DynamoDB with template information
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET template_data = :td, #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':td': {'S': json.dumps(selected_templates)},
                ':status': {'S': 'TEMPLATES_RETRIEVED'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Return response in AgentCore format
        return format_agent_response(200, {
            'session_id': session_id,
            'message': 'Templates retrieved successfully',
            'templates': selected_templates,
            'next_action': 'Templates have been selected. You can now proceed with document generation (SOW and/or PowerPoint).'
        })
        
    except Exception as e:
        print(f"[TEMPLATE RETRIEVER] ERROR: {str(e)}")
        return format_agent_response(500, f'Template retrieval failed: {str(e)}')

def format_agent_response(status_code, body):
    """Format response for Bedrock Agent action group"""
    if isinstance(body, dict):
        body_text = json.dumps(body)
    else:
        body_text = str(body)
    
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'TemplateRetriever',
            'apiPath': '/retrieve',
            'httpMethod': 'POST',
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': body_text
                }
            }
        }
    }

def select_best_templates(templates, requirements_data, cost_data):
    """Select the most appropriate templates based on project characteristics"""
    selected = {}
    
    # Simple template selection logic - in a real implementation, this would be more sophisticated
    complexity = requirements_data.get('complexity_level', 'Medium')
    total_cost = cost_data.get('total_cost', 50000)
    
    # Select SOW template
    if 'sow' in templates and templates['sow']:
        # For now, select the first available template
        # In practice, you'd match based on complexity, cost, industry, etc.
        if complexity == 'High' or total_cost > 100000:
            # Try to find enterprise template
            enterprise_template = next((t for t in templates['sow'] if 'enterprise' in t['name'].lower()), None)
            selected['sow'] = enterprise_template or templates['sow'][0]
        else:
            # Use standard template
            standard_template = next((t for t in templates['sow'] if 'standard' in t['name'].lower()), None)
            selected['sow'] = standard_template or templates['sow'][0]
    
    # Select PowerPoint template
    if 'powerpoint' in templates and templates['powerpoint']:
        if complexity == 'High' or total_cost > 100000:
            # Try to find detailed template
            detailed_template = next((t for t in templates['powerpoint'] if 'detailed' in t['name'].lower()), None)
            selected['powerpoint'] = detailed_template or templates['powerpoint'][0]
        else:
            # Use standard template
            standard_template = next((t for t in templates['powerpoint'] if 'standard' in t['name'].lower()), None)
            selected['powerpoint'] = standard_template or templates['powerpoint'][0]
    
    return selected