#!/usr/bin/env python3
import boto3
import json
from botocore.exceptions import ClientError

def get_account_id():
    """Get the current AWS account ID"""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def create_gateway_role(account_id):
    """Create IAM role for AgentCore Gateway"""
    iam = boto3.client('iam')
    role_name = 'AgentCoreGatewayRole'
    
    # Trust policy for Bedrock AgentCore to assume this role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permissions policy for invoking Lambda functions
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": [
                    f"arn:aws:lambda:us-east-1:{account_id}:function:ScopeSmithLambda-*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:*"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        # Create the role
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='IAM role for ScopeSmith AgentCore Gateway'
        )
        print(f"✓ Created IAM role: {role_name}")
        
        # Attach inline policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='AgentCoreGatewayPolicy',
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✓ Attached permissions policy to {role_name}")
        
        return response['Role']['Arn']
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"ℹ IAM role {role_name} already exists, using existing role")
            role = iam.get_role(RoleName=role_name)
            return role['Role']['Arn']
        else:
            raise e

def create_gateway(account_id, role_arn):
    """Create AgentCore Gateway"""
    client = boto3.client('bedrock-agent', region_name='us-east-1')
    
    try:
        response = client.create_agent_gateway(
            gatewayName='scopesmith-gateway',
            description='ScopeSmith Lambda functions exposed as MCP tools',
            gatewayType='LAMBDA'
        )
        
        gateway_arn = response['agentGateway']['agentGatewayArn']
        gateway_id = response['agentGateway']['agentGatewayId']
        
        print(f"\n✓ Gateway created successfully!")
        print(f"Gateway ARN: {gateway_arn}")
        print(f"Gateway ID: {gateway_id}")
        
        # Save to file for later use
        with open('gateway_config.json', 'w') as f:
            json.dump({
                'gateway_arn': gateway_arn,
                'gateway_id': gateway_id,
                'role_arn': role_arn,
                'account_id': account_id
            }, f, indent=2)
        print(f"\n✓ Configuration saved to gateway_config.json")
        
        return gateway_arn, gateway_id
        
    except ClientError as e:
        print(f"✗ Error creating gateway: {e}")
        raise e

def main():
    print("=" * 60)
    print("ScopeSmith AgentCore Gateway Setup")
    print("=" * 60)
    
    # Get AWS account ID
    account_id = get_account_id()
    print(f"\nAWS Account ID: {account_id}")
    
    # Create IAM role
    print("\n[1/2] Creating IAM role for AgentCore Gateway...")
    role_arn = create_gateway_role(account_id)
    print(f"Role ARN: {role_arn}")
    
    # Create Gateway
    print("\n[2/2] Creating AgentCore Gateway...")
    gateway_arn, gateway_id = create_gateway(account_id, role_arn)
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python add_gateway_targets.py")
    print("2. This will register your Lambda functions as gateway targets")
    print("=" * 60)

if __name__ == '__main__':
    main()
