#!/usr/bin/env python3
import json
import boto3
import time
from botocore.exceptions import ClientError

def get_stack_output(cloudformation, stack_name, output_key):
    try:
        response = cloudformation.describe_stacks(StackName=stack_name)
        for output in response['Stacks'][0]['Outputs']:
            if output['OutputKey'] == output_key:
                return output['OutputValue']
    except ClientError as e:
        print(f"Error getting stack output: {e}")
        return None

def create_gateway_role(iam_client, account_id):
    """Create IAM role for AgentCore Gateway"""
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
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='IAM role for ScopeSmith AgentCore Gateway'
        )
        print(f"✓ Created IAM role: {role_name}")
        
        # Attach inline policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='AgentCoreGatewayPolicy',
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✓ Attached permissions policy to {role_name}")
        
        return response['Role']['Arn']
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"ℹ IAM role {role_name} already exists, using existing role")
            role = iam_client.get_role(RoleName=role_name)
            return role['Role']['Arn']
        else:
            raise e

def create_agentcore_gateway(bedrock_agent, gateway_role_arn):
    """Create AgentCore Gateway for Lambda functions"""
    try:
        response = bedrock_agent.create_agent_gateway(
            gatewayName='scopesmith-gateway',
            description='ScopeSmith Lambda functions exposed as MCP tools',
            gatewayType='LAMBDA'
        )
        
        gateway_arn = response['agentGateway']['agentGatewayArn']
        gateway_id = response['agentGateway']['agentGatewayId']
        
        print(f"✓ Gateway created successfully!")
        print(f"  Gateway ARN: {gateway_arn}")
        print(f"  Gateway ID: {gateway_id}")
        
        return gateway_arn, gateway_id
        
    except ClientError as e:
        if 'already exists' in str(e).lower():
            print(f"ℹ Gateway already exists, skipping creation")
            # List existing gateways to find ours
            try:
                list_response = bedrock_agent.list_agent_gateways()
                for gw in list_response.get('agentGatewaySummaries', []):
                    if gw['agentGatewayName'] == 'scopesmith-gateway':
                        return gw['agentGatewayArn'], gw['agentGatewayId']
            except:
                pass
            return None, None
        print(f"✗ Error creating gateway: {e}")
        return None, None

def add_gateway_target(bedrock_agent, gateway_id, target_name, function_arn, input_schema):
    """Add a Lambda function as a gateway target"""
    try:
        bedrock_agent.create_agent_gateway_target(
            gatewayId=gateway_id,
            targetName=target_name,
            targetType='LAMBDA',
            targetConfiguration={
                'lambdaConfiguration': {
                    'lambdaArn': function_arn
                }
            },
            inputSchema=input_schema
        )
        print(f"  ✓ Added gateway target: {target_name}")
        return True
    except ClientError as e:
        if 'already exists' in str(e).lower():
            print(f"  ℹ Target {target_name} already exists")
            return True
        print(f"  ✗ Error adding target {target_name}: {e}")
        return False

def create_agentcore_memory(bedrock_agent, account_id):
    """Create AgentCore Memory for session context"""
    try:
        response = bedrock_agent.create_memory_configuration(
            memoryConfigurationName='scopesmith-memory',
            description='Stores requirements, cost data, and template paths across tool invocations',
            memoryType='SESSION_SUMMARY',
            memoryCapacityConfiguration={
                'maxTokens': 4096
            }
        )
        
        memory_arn = response['memoryConfiguration']['memoryConfigurationArn']
        memory_id = response['memoryConfiguration']['memoryConfigurationId']
        
        print(f"✓ Memory configuration created successfully!")
        print(f"  Memory ARN: {memory_arn}")
        print(f"  Memory ID: {memory_id}")
        
        return memory_arn, memory_id
        
    except ClientError as e:
        if 'already exists' in str(e).lower():
            print(f"ℹ Memory configuration already exists, skipping creation")
            # List existing memory configurations to find ours
            try:
                list_response = bedrock_agent.list_memory_configurations()
                for mem in list_response.get('memoryConfigurations', []):
                    if mem['memoryConfigurationName'] == 'scopesmith-memory':
                        return mem['memoryConfigurationArn'], mem['memoryConfigurationId']
            except:
                pass
            return None, None
        print(f"✗ Error creating memory configuration: {e}")
        return None, None

def create_agentcore_runtime(bedrock_agent, gateway_arn, memory_arn):
    """Create AgentCore Runtime for autonomous operation"""
    try:
        runtime_instruction = """You are ScopeSmith, an autonomous proposal generation agent. 

Your task: Convert client meeting notes into a complete project proposal (PowerPoint + SOW) in under 3 minutes.

Workflow:
1. Call analyze_requirements with the meeting notes to extract project scope, timeline, and technical details
2. Call calculate_project_cost with the extracted requirements to compute costs  
3. Call retrieve_templates with the project type to find the best templates
4. Call generate_powerpoint with requirements, costs, and template to create the presentation
5. Call generate_sow with the same data to create the Statement of Work
6. Return the S3 URLs for both documents

Use memory to pass data between steps. Work autonomously without asking for clarification."""

        response = bedrock_agent.create_agent_runtime(
            agentRuntimeName='scopesmith-runtime',
            description='Autonomous agent that converts meeting notes to complete proposals',
            foundationModel='anthropic.claude-3-5-sonnet-20241022-v2:0',
            instruction=runtime_instruction,
            gatewayConfigurations=[
                {'gatewayArn': gateway_arn}
            ],
            memoryConfiguration={
                'memoryArn': memory_arn
            },
            idleRuntimeSessionTimeout=900
        )
        
        runtime_arn = response['agentRuntime']['agentRuntimeArn']
        runtime_id = response['agentRuntime']['agentRuntimeId']
        
        print(f"✓ Runtime created successfully!")
        print(f"  Runtime ARN: {runtime_arn}")
        print(f"  Runtime ID: {runtime_id}")
        
        return runtime_arn, runtime_id
        
    except ClientError as e:
        print(f"✗ Error creating runtime: {e}")
        return None, None

def enable_cloudwatch_logging(logs_client, runtime_arn, account_id):
    """Enable CloudWatch logging for AgentCore Runtime"""
    try:
        runtime_id = runtime_arn.split('/')[-1]
        log_group_name = f'/aws/vendedlogs/bedrock-agentcore/runtime/{runtime_id}'
        
        # Create log group
        try:
            logs_client.create_log_group(logGroupName=log_group_name)
            print(f"✓ Created log group: {log_group_name}")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            print(f"ℹ Log group already exists: {log_group_name}")
        
        # Create delivery source
        try:
            logs_client.put_delivery_source(
                name=f"{runtime_id}-logs-source",
                logType="APPLICATION_LOGS",
                resourceArn=runtime_arn
            )
            print(f"✓ Created delivery source")
        except Exception as e:
            if 'already exists' not in str(e).lower():
                print(f"⚠ Warning creating delivery source: {e}")
        
        # Create delivery destination
        log_group_arn = f'arn:aws:logs:us-east-1:{account_id}:log-group:{log_group_name}'
        
        try:
            logs_client.put_delivery_destination(
                name=f"{runtime_id}-logs-destination",
                deliveryDestinationType='CWL',
                deliveryDestinationConfiguration={'destinationResourceArn': log_group_arn}
            )
            print(f"✓ Created delivery destination")
        except Exception as e:
            if 'already exists' not in str(e).lower():
                print(f"⚠ Warning creating delivery destination: {e}")
        
        print(f"✓ CloudWatch logging enabled for runtime")
        return log_group_name
        
    except Exception as e:
        print(f"✗ Error enabling CloudWatch logging: {e}")
        return None

def update_session_manager_for_runtime(lambda_client, function_name, runtime_arn, runtime_id):
    """Update session manager to use AgentCore Runtime instead of direct agent invocation"""
    try:
        # Get current function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Update with Runtime details
        current_env['AGENTCORE_RUNTIME_ARN'] = runtime_arn
        current_env['AGENTCORE_RUNTIME_ID'] = runtime_id
        
        # Update the function
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': current_env}
        )
        
        print(f"✓ Updated {function_name} with Runtime ARN and ID")
        return True
        
    except ClientError as e:
        print(f"✗ Error updating session manager: {e}")
        return False

def main():
    # Initialize AWS clients
    cloudformation = boto3.client('cloudformation')
    bedrock_agent = boto3.client('bedrock-agent')
    lambda_client = boto3.client('lambda')
    iam_client = boto3.client('iam')
    logs_client = boto3.client('logs')

    # Get Lambda function ARNs from CloudFormation outputs
    lambda_functions = {
        'RequirementsAnalyzer': {
            'description': 'Analyzes client requirements using Claude 3.5 Sonnet',
            'schema': {
                'type': 'object',
                'properties': {
                    'requirements': {'type': 'string', 'description': 'The client requirements to analyze'},
                    'session_id': {'type': 'string', 'description': 'Unique session identifier'}
                },
                'required': ['requirements', 'session_id']
            }
        },
        'CostCalculator': {
            'description': 'Calculates project costs based on requirements',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string', 'description': 'Unique session identifier'},
                    'requirements_data': {'type': 'string', 'description': 'JSON string containing analyzed requirements data'}
                },
                'required': ['session_id', 'requirements_data']
            }
        },
        'TemplateRetriever': {
            'description': 'Retrieves and manages document templates',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string', 'description': 'Unique session identifier'},
                    'template_type': {'type': 'string', 'enum': ['powerpoint', 'sow'], 'description': 'Type of template to retrieve'}
                },
                'required': ['session_id', 'template_type']
            }
        },
        'PowerPointGenerator': {
            'description': 'Generates PowerPoint presentations',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string', 'description': 'Unique session identifier'},
                    'template_path': {'type': 'string', 'description': 'Path to the PowerPoint template'},
                    'proposal_data': {'type': 'string', 'description': 'JSON string containing proposal data'}
                },
                'required': ['session_id', 'template_path', 'proposal_data']
            }
        },
        'SOWGenerator': {
            'description': 'Generates Statement of Work documents',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string', 'description': 'Unique session identifier'},
                    'template_path': {'type': 'string', 'description': 'Path to the SOW template'},
                    'proposal_data': {'type': 'string', 'description': 'JSON string containing proposal data'}
                },
                'required': ['session_id', 'template_path', 'proposal_data']
            }
        }
    }

    # Get Lambda function ARNs
    function_arns = {}
    for function_name in lambda_functions.keys():
        arn = get_stack_output(cloudformation, 'ScopeSmithLambda', f'{function_name}FunctionArn')
        if arn:
            function_arns[function_name] = arn
            print(f"Found {function_name} ARN: {arn}")
        else:
            print(f"Failed to get ARN for {function_name}")
            return

    # Get Session Manager ARN
    session_manager_arn = get_stack_output(cloudformation, 'ScopeSmithLambda', 'SessionManagerFunctionArn')
    if not session_manager_arn:
        print("Failed to get Session Manager ARN")
        return

    account_id = boto3.client('sts').get_caller_identity().get('Account')

    # Create Gateway Role
    print("\n[1/5] Creating Gateway Role...")
    gateway_role_arn = create_gateway_role(iam_client, account_id)
    print(f"✅ Gateway Role ARN: {gateway_role_arn}")
    
    # Create AgentCore Gateway
    print("\n[2/5] Creating AgentCore Gateway...")
    gateway_arn, gateway_id = create_agentcore_gateway(bedrock_agent, gateway_role_arn)
    
    if not gateway_arn or not gateway_id:
        print("❌ Failed to create AgentCore Gateway")
        return
    
    print(f"✅ Gateway ARN: {gateway_arn}")
    print(f"✅ Gateway ID: {gateway_id}")
    
    # Add Lambda functions as Gateway targets
    print("\n   Adding Lambda functions as Gateway targets...")
    for function_name, function_data in lambda_functions.items():
        add_gateway_target(
            bedrock_agent,
            gateway_id,
            function_name,
            function_arns[function_name],
            function_data['schema']
        )
    
    # Create AgentCore Memory
    print("\n[3/5] Creating AgentCore Memory...")
    memory_arn, memory_id = create_agentcore_memory(bedrock_agent, account_id)
    
    if not memory_arn or not memory_id:
        print("❌ Failed to create AgentCore Memory")
        return
    
    print(f"✅ Memory ARN: {memory_arn}")
    
    # Create AgentCore Runtime
    print("\n[4/5] Creating AgentCore Runtime...")
    runtime_arn, runtime_id = create_agentcore_runtime(bedrock_agent, gateway_arn, memory_arn)
    
    if not runtime_arn or not runtime_id:
        print("❌ Failed to create AgentCore Runtime")
        return
    
    print(f"✅ Runtime ARN: {runtime_arn}")
    print(f"✅ Runtime ID: {runtime_id}")
    
    # Enable CloudWatch logging
    print("\n[5/5] Enabling CloudWatch logging...")
    log_group_name = enable_cloudwatch_logging(logs_client, runtime_arn, account_id)
    print(f"✅ CloudWatch Log Group: {log_group_name}")
    
    # Update Session Manager to use Runtime
    print("\n   Updating Session Manager Lambda...")
    session_manager_function_name = session_manager_arn.split(':')[-1]
    update_session_manager_for_runtime(
        lambda_client, session_manager_function_name, runtime_arn, runtime_id
    )
    
    print("\n" + "="*70)
    print("🎉 AgentCore Runtime Setup Complete!")
    print("="*70)
    print(f"\n✅ Gateway ARN: {gateway_arn}")
    print(f"✅ Gateway ID: {gateway_id}")
    print(f"✅ Memory ARN: {memory_arn}")
    print(f"✅ Runtime ARN: {runtime_arn}")
    print(f"✅ Runtime ID: {runtime_id}")
    print(f"✅ CloudWatch Log Group: {log_group_name}")
    print(f"\n✅ Lambda Functions Connected: {list(lambda_functions.keys())}")
    print("\n🚀 Your ScopeSmith system is now using AgentCore Runtime!")
    print("   Workflow: Frontend → Session Manager → AgentCore Runtime → Gateway → Lambda Functions")
    print("="*70)

if __name__ == "__main__":
    main()