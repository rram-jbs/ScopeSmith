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
            "total": 0
        },
        "junior_developer": {
            "hours": int(total_hours * 0.3),
            "rate": default_rates["junior_developer"],
            "total": 0
        },
        "project_manager": {
            "hours": int(total_hours * 0.15),
            "rate": default_rates["project_manager"],
            "total": 0
        },
        "designer": {
            "hours": int(total_hours * 0.1),
            "rate": default_rates["designer"],
            "total": 0
        },
        "qa_engineer": {
            "hours": int(total_hours * 0.05),
            "rate": default_rates["qa_engineer"],
            "total": 0
        }
    }
    
    # Calculate totals
    total_cost = 0
    for role, data in cost_breakdown.items():
        data["total"] = data["hours"] * data["rate"]
        total_cost += data["total"]
    
    return {
        "total_hours": total_hours,
        "total_cost": total_cost,
        "cost_breakdown": cost_breakdown,
        "complexity_level": complexity,
        "project_duration_weeks": max(4, total_hours // 40)
    }

def handler(event, context):
    try:
        session_id = event['session_id']
        requirements_data = event['requirements_data']
        
        # Initialize AWS clients
        dynamodb = boto3.client('dynamodb')
        lambda_client = boto3.client('lambda')
        
        # Update status
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
        
        # Calculate project costs
        cost_data = calculate_project_cost(requirements_data)
        
        # Update DynamoDB with cost data
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET cost_data = :cd, #status = :status, updated_at = :ua',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':cd': {'S': json.dumps(cost_data)},
                ':status': {'S': 'COSTS_CALCULATED'},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Invoke template retriever to get templates
        if os.environ.get('TEMPLATE_RETRIEVER_ARN'):
            lambda_client.invoke(
                FunctionName=os.environ['TEMPLATE_RETRIEVER_ARN'],
                InvocationType='Event',
                Payload=json.dumps({
                    'session_id': session_id,
                    'template_type': 'both'  # Request both PowerPoint and SOW templates
                })
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'session_id': session_id,
                'message': 'Cost calculation complete',
                'cost_data': cost_data
            })
        }
        
    except Exception as e:
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
                    ':error': {'S': f'Cost calculation failed: {str(e)}'},
                    ':ua': {'S': datetime.utcnow().isoformat()}
                }
            )
        except:
            pass
            
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }