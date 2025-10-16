import os
import json
import boto3
from datetime import datetime
from decimal import Decimal

def calculate_project_cost(requirements_data):
    """Calculate project cost based on requirements analysis"""
    # Default rates (this would normally come from the rate sheets table)
    default_rates = {
        "senior_developer": 150,
        "junior_developer": 100,
        "project_manager": 120,
        "designer": 110,
        "qa_engineer": 90
    }
    
    complexity_multipliers = {
        "Low": 1.0,
        "Medium": 1.5,
        "High": 2.0
    }
    
    # Extract data from requirements analysis
    complexity = requirements_data.get("complexity_level", "Medium")
    deliverables_count = len(requirements_data.get("deliverables", []))
    technical_requirements_count = len(requirements_data.get("technical_requirements", []))
    
    # Base calculation
    base_hours = max(80, deliverables_count * 40 + technical_requirements_count * 20)
    complexity_multiplier = complexity_multipliers.get(complexity, 1.5)
    total_hours = int(base_hours * complexity_multiplier)
    
    # Calculate costs by role
    cost_breakdown = {
        "senior_developer": {
            "hours": int(total_hours * 0.4),
            "rate": default_rates["senior_developer"],
            "amount": int(total_hours * 0.4) * default_rates["senior_developer"]
        },
        "junior_developer": {
            "hours": int(total_hours * 0.3),
            "rate": default_rates["junior_developer"],
            "amount": int(total_hours * 0.3) * default_rates["junior_developer"]
        },
        "project_manager": {
            "hours": int(total_hours * 0.15),
            "rate": default_rates["project_manager"],
            "amount": int(total_hours * 0.15) * default_rates["project_manager"]
        },
        "designer": {
            "hours": int(total_hours * 0.10),
            "rate": default_rates["designer"],
            "amount": int(total_hours * 0.10) * default_rates["designer"]
        },
        "qa_engineer": {
            "hours": int(total_hours * 0.05),
            "rate": default_rates["qa_engineer"],
            "amount": int(total_hours * 0.05) * default_rates["qa_engineer"]
        }
    }
    
    total_cost = sum(role["amount"] for role in cost_breakdown.values())
    
    return {
        "total_hours": total_hours,
        "total_cost": total_cost,
        "complexity_level": complexity,
        "cost_breakdown": cost_breakdown
    }

def handler(event, context):
    """
    AgentCore Action Group Function for Cost Calculation
    This function is invoked by the Bedrock Agent to calculate project costs
    """
    try:
        print(f"[COST CALCULATOR] Received event: {json.dumps(event)}")
        
        # Check if this is a Bedrock Agent action group invocation
        if 'agent' in event or 'actionGroup' in event or 'function' in event:
            print(f"[COST CALCULATOR] Bedrock Agent action group invocation detected")
            
            parameters = event.get('parameters', [])
            param_dict = {}
            for param in parameters:
                param_name = param['name']
                param_value = param['value']
                
                # Handle nested JSON in parameters
                if param_name == 'requirements_data':
                    try:
                        # Try to parse as JSON if it's a string
                        if isinstance(param_value, str):
                            param_dict[param_name] = json.loads(param_value)
                        else:
                            param_dict[param_name] = param_value
                    except json.JSONDecodeError as e:
                        print(f"[COST CALCULATOR] JSON decode error for requirements_data: {str(e)}")
                        print(f"[COST CALCULATOR] Raw value: {param_value[:500]}...")
                        # If it fails, store as-is and handle later
                        param_dict[param_name] = param_value
                else:
                    param_dict[param_name] = param_value
            
            session_id = param_dict.get('session_id')
            requirements_data = param_dict.get('requirements_data')
        elif 'inputText' in event:
            try:
                params = json.loads(event['inputText'])
                session_id = params['session_id']
                requirements_data = params.get('requirements_data')
                if isinstance(requirements_data, str):
                    requirements_data = json.loads(requirements_data)
            except (json.JSONDecodeError, KeyError) as e:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Invalid input format from AgentCore: {str(e)}'
                    })
                }
        else:
            return format_agent_response(400, 'Missing required parameters')

        print(f"[COST CALCULATOR] Starting cost calculation for session: {session_id}")
        
        # Initialize AWS clients
        bedrock = boto3.client('bedrock-runtime')
        dynamodb = boto3.client('dynamodb')
        
        # Update status to calculating costs
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'CALCULATING_COSTS'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Get requirements data from session
        response = dynamodb.get_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}}
        )
        
        if 'Item' not in response:
            raise ValueError(f"Session {session_id} not found")
        
        session_data = response['Item']
        requirements_data_str = session_data.get('requirements_data', {}).get('S', '{}')
        
        try:
            requirements_data_full = json.loads(requirements_data_str)
            # Extract the analysis for cost calculation
            analysis_data = requirements_data_full.get('analysis', {})
            raw_requirements = requirements_data_full.get('raw_requirements', '')
        except json.JSONDecodeError:
            raise ValueError("Invalid requirements data format in session")
        
        # Calculate project cost based on analysis
        cost_result = calculate_project_cost(analysis_data)
        
        # Call Amazon Nova Pro to estimate additional costs and validate calculations
        # Include BOTH raw requirements and analysis for full context
        prompt = f"""Analyze this project data and provide a cost breakdown validation and recommendations.

RAW PROJECT REQUIREMENTS (Original User Input):
{raw_requirements}

ANALYZED PROJECT DATA:
{json.dumps(analysis_data, indent=2)}

CALCULATED COST ESTIMATES:
{json.dumps(cost_result, indent=2)}

Based on the complete project context, provide recommendations in JSON format with the following structure (no markdown, no code blocks):
{{
    "resource_allocation_recommendations": ["List of recommendations"],
    "risk_contingency_percentage": "Recommended percentage as number (e.g., 15)",
    "hidden_costs_to_consider": ["List of potential hidden costs"],
    "cost_saving_opportunities": ["List of opportunities"],
    "overall_assessment": "Brief assessment of the cost estimate accuracy"
}}"""
        
        print(f"[COST CALCULATOR] Calling Bedrock model for cost validation...")
        
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
                    "max_new_tokens": 1500,
                    "temperature": 0.5
                }
            })
        )
        
        result = json.loads(response['body'].read().decode())
        print(f"[COST CALCULATOR] Bedrock response received")
        
        # Parse the response - handle different response structures
        ai_insights_content = None
        if 'content' in result and len(result['content']) > 0:
            ai_insights_content = result['content'][0].get('text', '')
        elif 'output' in result:
            if isinstance(result['output'], dict) and 'message' in result['output']:
                message = result['output']['message']
                if 'content' in message and len(message['content']) > 0:
                    ai_insights_content = message['content'][0].get('text', '')
        
        if not ai_insights_content:
            print(f"[COST CALCULATOR] WARNING: Could not extract text from model response")
            ai_insights_content = '{"overall_assessment": "Cost calculation completed successfully"}'
        
        # Try to parse AI insights as JSON
        try:
            # Remove markdown code blocks if present
            if '```json' in ai_insights_content:
                ai_insights_content = ai_insights_content.split('```json')[1].split('```')[0].strip()
            elif '```' in ai_insights_content:
                ai_insights_content = ai_insights_content.split('```')[1].split('```')[0].strip()
            
            ai_insights = json.loads(ai_insights_content)
        except json.JSONDecodeError:
            print(f"[COST CALCULATOR] Could not parse AI insights as JSON, using default")
            ai_insights = {
                "overall_assessment": "Cost calculation completed based on project analysis",
                "risk_contingency_percentage": "15",
                "resource_allocation_recommendations": ["Review resource allocation with project requirements"],
                "hidden_costs_to_consider": ["Infrastructure costs", "Training costs", "Maintenance"],
                "cost_saving_opportunities": ["Optimize resource utilization"]
            }
        
        # Combine cost result with AI insights
        cost_result['ai_insights'] = ai_insights
        
        # Update DynamoDB with cost calculation results
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET cost_data = :cd, #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':cd': {'S': json.dumps(cost_result)},
                ':status': {'S': 'COSTS_CALCULATED'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        print(f"[COST CALCULATOR] Cost calculation complete")
        
        # Return response in AgentCore format
        return format_agent_response(200, {
            'session_id': session_id,
            'message': 'Cost calculation completed successfully',
            'cost_result': cost_result
        })
        
    except Exception as e:
        print(f"[COST CALCULATOR] ERROR: {str(e)}")
        import traceback
        print(f"[COST CALCULATOR] Traceback: {traceback.format_exc()}")
        try:
            if 'session_id' in locals():
                dynamodb = boto3.client('dynamodb')
                dynamodb.update_item(
                    TableName=os.environ['SESSIONS_TABLE_NAME'],
                    Key={'session_id': {'S': session_id}},
                    UpdateExpression='SET #status = :status, error_message = :error, updated_at = :ua',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'ERROR'},
                        ':error': {'S': f'Cost calculation failed: {str(e)}'},
                        ':ua': {'S': datetime.utcnow().isoformat()}
                    }
                )
        except:
            pass
            
        return format_agent_response(500, f'Cost calculation failed: {str(e)}')

def format_agent_response(status_code, body):
    """Format response for Bedrock Agent action group"""
    if isinstance(body, dict):
        body_text = json.dumps(body)
    else:
        body_text = str(body)
    
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'CostCalculator',
            'function': 'costcalculator',  # Must match function name in action group
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': body_text
                    }
                }
            }
        }
    }