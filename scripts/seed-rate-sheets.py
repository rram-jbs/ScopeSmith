#!/usr/bin/env python3
import boto3
import json
from botocore.exceptions import ClientError

def get_table_name():
    cloudformation = boto3.client('cloudformation')
    try:
        response = cloudformation.describe_stacks(StackName='ScopeSmithInfrastructure')
        for output in response['Stacks'][0]['Outputs']:
            if output['OutputKey'] == 'RateSheetsTableName':
                return output['OutputValue']
    except ClientError as e:
        print(f"Error getting table name: {e}")
        return None

def seed_rate_sheets():
    table_name = get_table_name()
    if not table_name:
        print("Failed to get rate sheets table name")
        return

    dynamodb = boto3.client('dynamodb')
    
    # Define role-based pricing data
    rate_sheets = [
        {
            'role_id': 'architect',
            'role_name': 'Solutions Architect',
            'hourly_rate': 200.00,
            'category': 'architecture',
            'description': 'System design and technical leadership'
        },
        {
            'role_id': 'senior_dev',
            'role_name': 'Senior Developer',
            'hourly_rate': 150.00,
            'category': 'development',
            'description': 'Advanced development and code review'
        },
        {
            'role_id': 'dev',
            'role_name': 'Developer',
            'hourly_rate': 100.00,
            'category': 'development',
            'description': 'Software development and testing'
        },
        {
            'role_id': 'qa',
            'role_name': 'Quality Assurance',
            'hourly_rate': 90.00,
            'category': 'quality',
            'description': 'Testing and quality assurance'
        },
        {
            'role_id': 'pm',
            'role_name': 'Project Manager',
            'hourly_rate': 125.00,
            'category': 'management',
            'description': 'Project coordination and client communication'
        },
        {
            'role_id': 'devops',
            'role_name': 'DevOps Engineer',
            'hourly_rate': 140.00,
            'category': 'operations',
            'description': 'Infrastructure and deployment automation'
        }
    ]
    
    try:
        for rate in rate_sheets:
            dynamodb.put_item(
                TableName=table_name,
                Item={
                    'role_id': {'S': rate['role_id']},
                    'role_name': {'S': rate['role_name']},
                    'hourly_rate': {'N': str(rate['hourly_rate'])},
                    'category': {'S': rate['category']},
                    'description': {'S': rate['description']}
                }
            )
            print(f"Added rate sheet for {rate['role_name']}")
            
        print("Successfully seeded rate sheets table")
        
    except ClientError as e:
        print(f"Error seeding rate sheets: {e}")

if __name__ == "__main__":
    seed_rate_sheets()