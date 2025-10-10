import os
import json
import boto3
from datetime import datetime

def handler(event, context):
    try:
        session_id = event['session_id']
        requirements_data = event['requirements_data']
        
        # Get session data to access team_size
        dynamodb = boto3.client('dynamodb')
        session_response = dynamodb.get_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}}
        )
        
        if 'Item' not in session_response:
            raise Exception('Session not found')
            
        team_size = int(session_response['Item']['team_size']['N'])
        duration = session_response['Item']['duration']['S']
        
        # Convert duration to weeks
        duration_mapping = {
            'SHORT': 4,    # 1 month
            'MEDIUM': 12,  # 3 months
            'LONG': 24    # 6 months
        }
        weeks = duration_mapping.get(duration.upper(), 12)
        
        # Get rate sheet data
        rate_sheets_response = dynamodb.scan(
            TableName=os.environ['RATE_SHEETS_TABLE_NAME']
        )
        
        total_cost = 0
        cost_breakdown = {}
        
        # Calculate hours per week based on team size
        hours_per_week = team_size * 40  # Assuming 40 hours per team member per week
        
        for role in rate_sheets_response['Items']:
            role_id = role['role_id']['S']
            hourly_rate = float(role['hourly_rate']['N'])
            
            # Calculate role-specific hours based on team composition
            role_percentage = {
                'developer': 0.6,
                'designer': 0.2,
                'project_manager': 0.1,
                'qa': 0.1
            }.get(role_id.lower(), 0.25)  # Default to 25% if role not specified
            
            estimated_hours = hours_per_week * weeks * role_percentage
            
            cost_breakdown[role_id] = {
                'hours': estimated_hours,
                'rate': hourly_rate,
                'subtotal': estimated_hours * hourly_rate
            }
            total_cost += estimated_hours * hourly_rate
        
        cost_data = {
            'total_cost': total_cost,
            'breakdown': cost_breakdown,
            'currency': 'USD',
            'team_size': team_size,
            'duration_weeks': weeks,
            'hours_per_week': hours_per_week
        }
        
        # Update session with cost data
        dynamodb.update_item(
            TableName=os.environ['SESSIONS_TABLE_NAME'],
            Key={'session_id': {'S': session_id}},
            UpdateExpression='SET cost_data = :cd, updated_at = :ua',
            ExpressionAttributeValues={
                ':cd': {'S': json.dumps(cost_data)},
                ':ua': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'session_id': session_id,
                'cost_data': cost_data
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }