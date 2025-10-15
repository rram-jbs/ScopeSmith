import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    try:
        # Handle both direct Lambda invocation and AgentCore Gateway calls
        if 'session_id' in event and 'requirements' in event:
            session_id = event['session_id']
            requirements = event['requirements']
        elif 'inputText' in event:
            # AgentCore Gateway invocation
            try:
                params = json.loads(event['inputText'])
                session_id = params['session_id']
                requirements = params['requirements']
            except (json.JSONDecodeError, KeyError) as e:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Invalid input format from AgentCore: {str(e)}'
                    })
                }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters: session_id and requirements'
                })
            }

        print(f"[REQUIREMENTS ANALYZER] Starting requirements analysis")
        print(f"[REQUIREMENTS ANALYZER] Event received: {json.dumps(event)}")
        
        print(f"[REQUIREMENTS ANALYZER] Session ID: {session_id}")
        print(f"[REQUIREMENTS ANALYZER] Requirements length: {len(requirements)} characters")
        
        # Initialize AWS clients
        bedrock = boto3.client('bedrock-runtime')
        dynamodb = boto3.client('dynamodb')
        lambda_client = boto3.client('lambda')
        
        # Update status to analyzing
        print(f"[REQUIREMENTS ANALYZER] Updating session status to ANALYZING_REQUIREMENTS")
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
        
        print(f"[REQUIREMENTS ANALYZER] Invoking Bedrock model: {os.environ.get('BEDROCK_MODEL_ID', 'NOT_SET')}")
        print(f"[REQUIREMENTS ANALYZER] Prompt length: {len(prompt)} characters")
        
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
        
        print(f"[REQUIREMENTS ANALYZER] Bedrock response received successfully")
        
        result = json.loads(response['body'].read().decode())
        analysis_content = result.get('content', [{}])[0].get('text', '{}')
        
        print(f"[REQUIREMENTS ANALYZER] Analysis content length: {len(analysis_content)} characters")
        print(f"[REQUIREMENTS ANALYZER] Raw analysis content: {analysis_content[:500]}...")
        
        # Parse the analysis result
        try:
            analysis_result = json.loads(analysis_content)
            print(f"[REQUIREMENTS ANALYZER] Successfully parsed JSON analysis result")
            print(f"[REQUIREMENTS ANALYZER] Analysis keys: {list(analysis_result.keys())}")
        except json.JSONDecodeError as e:
            print(f"[REQUIREMENTS ANALYZER] WARNING: Failed to parse JSON from Claude response: {str(e)}")
            print(f"[REQUIREMENTS ANALYZER] Using fallback analysis result")
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
        print(f"[REQUIREMENTS ANALYZER] Updating DynamoDB with analysis results")
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
        print(f"[REQUIREMENTS ANALYZER] Session status updated to REQUIREMENTS_ANALYZED")
        
        # Invoke cost calculator with the analysis results
        if os.environ.get('COST_CALCULATOR_ARN'):
            print(f"[REQUIREMENTS ANALYZER] Invoking cost calculator: {os.environ['COST_CALCULATOR_ARN']}")
            lambda_client.invoke(
                FunctionName=os.environ['COST_CALCULATOR_ARN'],
                InvocationType='Event',
                Payload=json.dumps({
                    'session_id': session_id,
                    'requirements_data': analysis_result
                })
            )
            print(f"[REQUIREMENTS ANALYZER] Cost calculator invoked successfully")
        else:
            print(f"[REQUIREMENTS ANALYZER] WARNING: COST_CALCULATOR_ARN not set, skipping cost calculation")
        
        print(f"[REQUIREMENTS ANALYZER] Analysis complete for session: {session_id}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'session_id': session_id,
                'message': 'Requirements analysis complete',
                'analysis_result': analysis_result
            })
        }
        
    except Exception as e:
        print(f"[REQUIREMENTS ANALYZER] ERROR: Analysis failed with exception: {str(e)}")
        print(f"[REQUIREMENTS ANALYZER] ERROR: Exception type: {type(e).__name__}")
        import traceback
        print(f"[REQUIREMENTS ANALYZER] ERROR: Traceback:\n{traceback.format_exc()}")
        
        # Update session with error status
        try:
            print(f"[REQUIREMENTS ANALYZER] Updating session with error status")
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
            print(f"[REQUIREMENTS ANALYZER] Session error status updated successfully")
        except Exception as db_error:
            print(f"[REQUIREMENTS ANALYZER] ERROR: Failed to update session error status: {str(db_error)}")
            
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }