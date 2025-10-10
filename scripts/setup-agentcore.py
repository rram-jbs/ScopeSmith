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

def create_agent_runtime(bedrock_agent):
    try:
        response = bedrock_agent.create_agent_runtime(
            runtimeName="ScopeSmithRuntime",
            description="Runtime for ScopeSmith proposal generation system",
            memoryConfiguration={
                "scopeType": "SESSION",
                "memoryTtl": "1d"
            }
        )
        return response['agentRuntime']['agentRuntimeId']
    except ClientError as e:
        print(f"Error creating agent runtime: {e}")
        return None

def register_lambda_tool(bedrock_agent, runtime_id, function_arn, tool_name, description, schema):
    try:
        response = bedrock_agent.create_agent_gateway(
            agentRuntimeId=runtime_id,
            description=description,
            gatewayConfiguration={
                "lambda": {
                    "lambda_function_arn": function_arn
                }
            },
            gatewayParameters=schema,
            gatewayName=tool_name
        )
        return response['agentGateway']['agentGatewayId']
    except ClientError as e:
        print(f"Error registering lambda tool: {e}")
        return None

def main():
    # Initialize AWS clients
    cloudformation = boto3.client('cloudformation')
    bedrock_agent = boto3.client('bedrock-agent')

    # Get Lambda function ARNs from CloudFormation outputs
    lambda_functions = {
        'RequirementsAnalyzer': {
            'description': 'Analyzes client requirements using Claude 3.5 Sonnet',
            'schema': {
                'type': 'object',
                'properties': {
                    'requirements': {'type': 'string'},
                    'session_id': {'type': 'string'}
                },
                'required': ['requirements', 'session_id']
            }
        },
        'CostCalculator': {
            'description': 'Calculates project costs based on requirements',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string'},
                    'requirements_data': {'type': 'object'}
                },
                'required': ['session_id', 'requirements_data']
            }
        },
        'TemplateRetriever': {
            'description': 'Retrieves and manages document templates',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string'},
                    'template_type': {'type': 'string', 'enum': ['powerpoint', 'sow']}
                },
                'required': ['session_id', 'template_type']
            }
        },
        'PowerPointGenerator': {
            'description': 'Generates PowerPoint presentations',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string'},
                    'template_path': {'type': 'string'},
                    'proposal_data': {'type': 'object'}
                },
                'required': ['session_id', 'template_path', 'proposal_data']
            }
        },
        'SOWGenerator': {
            'description': 'Generates Statement of Work documents',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string'},
                    'template_path': {'type': 'string'},
                    'proposal_data': {'type': 'object'}
                },
                'required': ['session_id', 'template_path', 'proposal_data']
            }
        }
    }

    function_arns = {}
    for function_name in lambda_functions.keys():
        arn = get_stack_output(cloudformation, 'ScopeSmithLambda', f'{function_name}FunctionArn')
        if arn:
            function_arns[function_name] = arn
        else:
            print(f"Failed to get ARN for {function_name}")
            return

    # Create AgentCore runtime
    runtime_id = create_agent_runtime(bedrock_agent)
    if not runtime_id:
        print("Failed to create agent runtime")
        return

    print(f"Created agent runtime with ID: {runtime_id}")

    # Register Lambda functions as tools
    for function_name, function_data in lambda_functions.items():
        gateway_id = register_lambda_tool(
            bedrock_agent,
            runtime_id,
            function_arns[function_name],
            function_name,
            function_data['description'],
            function_data['schema']
        )
        if gateway_id:
            print(f"Registered {function_name} with gateway ID: {gateway_id}")
        else:
            print(f"Failed to register {function_name}")

    print("AgentCore setup complete!")

if __name__ == "__main__":
    main()