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

def create_bedrock_agent(bedrock_agent):
    """Create a Bedrock Agent for ScopeSmith"""
    try:
        response = bedrock_agent.create_agent(
            agentName="ScopeSmithAgent",
            description="AI agent for proposal generation system",
            foundationModel="anthropic.claude-3-5-sonnet-20241022-v2:0",
            instruction="""You are ScopeSmith, an AI assistant specialized in generating professional proposals and statements of work. 
            You help analyze client requirements, calculate costs, and generate comprehensive proposals with PowerPoint presentations and SOW documents.
            
            Your capabilities include:
            - Analyzing client requirements and breaking them down into deliverables
            - Calculating project costs based on standard rate sheets
            - Retrieving appropriate document templates
            - Generating customized PowerPoint presentations
            - Creating detailed Statements of Work
            
            Always maintain a professional tone and ensure all outputs are well-structured and comprehensive.""",
            idleSessionTTLInSeconds=3600
        )
        return response['agent']['agentId']
    except ClientError as e:
        print(f"Error creating Bedrock agent: {e}")
        return None

def create_agent_action_group(bedrock_agent, agent_id, function_arn, action_group_name, description, schema):
    """Create an action group for the Bedrock agent with Lambda function"""
    try:
        # Convert our schema to the format expected by Bedrock Agents
        function_parameters = {}
        
        # Add each property as a parameter
        for prop_name, prop_config in schema['properties'].items():
            param_type = prop_config['type']
            
            # Convert 'object' type to 'string' since Bedrock only supports primitive types
            if param_type == 'object':
                param_type = 'string'
            
            function_parameters[prop_name] = {
                'description': prop_config.get('description', f'Parameter {prop_name}'),
                'type': param_type,
                'required': prop_name in schema.get('required', [])
            }
            
            # Add enum values to description instead of as separate field
            if 'enum' in prop_config:
                enum_values = ', '.join(prop_config['enum'])
                function_parameters[prop_name]['description'] += f' (allowed values: {enum_values})'
        
        response = bedrock_agent.create_agent_action_group(
            agentId=agent_id,
            agentVersion="DRAFT",
            actionGroupName=action_group_name,
            description=description,
            actionGroupExecutor={
                'lambda': function_arn
            },
            functionSchema={
                'functions': [
                    {
                        'name': action_group_name.lower(),
                        'description': description,
                        'parameters': function_parameters
                    }
                ]
            }
        )
        return response['agentActionGroup']['actionGroupId']
    except ClientError as e:
        print(f"Error creating action group {action_group_name}: {e}")
        return None

def wait_for_agent_ready(bedrock_agent, agent_id, max_attempts=12, wait_time=10):
    """Wait for agent to be in PREPARED or NOT_PREPARED state"""
    for attempt in range(max_attempts):
        try:
            response = bedrock_agent.get_agent(agentId=agent_id)
            agent_status = response['agent']['agentStatus']
            print(f"Agent status (attempt {attempt + 1}): {agent_status}")
            
            if agent_status in ['PREPARED', 'NOT_PREPARED', 'FAILED']:
                return agent_status
            
            if attempt < max_attempts - 1:
                print(f"Waiting {wait_time} seconds for agent to be ready...")
                time.sleep(wait_time)
                
        except ClientError as e:
            print(f"Error checking agent status: {e}")
            if attempt < max_attempts - 1:
                time.sleep(wait_time)
    
    return None

def prepare_agent(bedrock_agent, agent_id):
    """Prepare the agent for use"""
    try:
        response = bedrock_agent.prepare_agent(agentId=agent_id)
        return response['agentStatus']
    except ClientError as e:
        print(f"Error preparing agent: {e}")
        return None

def create_agent_alias(bedrock_agent, agent_id):
    """Create an alias for the agent"""
    try:
        response = bedrock_agent.create_agent_alias(
            agentId=agent_id,
            agentAliasName="prod",
            description="Production alias for ScopeSmith agent"
        )
        return response['agentAlias']['agentAliasId']
    except ClientError as e:
        print(f"Error creating agent alias: {e}")
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
                    'requirements': {
                        'type': 'string',
                        'description': 'The client requirements to analyze'
                    },
                    'session_id': {
                        'type': 'string', 
                        'description': 'Unique session identifier'
                    }
                },
                'required': ['requirements', 'session_id']
            }
        },
        'CostCalculator': {
            'description': 'Calculates project costs based on requirements',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {
                        'type': 'string',
                        'description': 'Unique session identifier'
                    },
                    'requirements_data': {
                        'type': 'string',
                        'description': 'JSON string containing analyzed requirements data'
                    }
                },
                'required': ['session_id', 'requirements_data']
            }
        },
        'TemplateRetriever': {
            'description': 'Retrieves and manages document templates',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {
                        'type': 'string',
                        'description': 'Unique session identifier'
                    },
                    'template_type': {
                        'type': 'string', 
                        'enum': ['powerpoint', 'sow'],
                        'description': 'Type of template to retrieve'
                    }
                },
                'required': ['session_id', 'template_type']
            }
        },
        'PowerPointGenerator': {
            'description': 'Generates PowerPoint presentations',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {
                        'type': 'string',
                        'description': 'Unique session identifier'
                    },
                    'template_path': {
                        'type': 'string',
                        'description': 'Path to the PowerPoint template'
                    },
                    'proposal_data': {
                        'type': 'string',
                        'description': 'JSON string containing proposal data for presentation generation'
                    }
                },
                'required': ['session_id', 'template_path', 'proposal_data']
            }
        },
        'SOWGenerator': {
            'description': 'Generates Statement of Work documents',
            'schema': {
                'type': 'object',
                'properties': {
                    'session_id': {
                        'type': 'string',
                        'description': 'Unique session identifier'
                    },
                    'template_path': {
                        'type': 'string',
                        'description': 'Path to the SOW template'
                    },
                    'proposal_data': {
                        'type': 'string',
                        'description': 'JSON string containing proposal data for SOW generation'
                    }
                },
                'required': ['session_id', 'template_path', 'proposal_data']
            }
        }
    }

    # Get Lambda function ARNs from CloudFormation stack outputs
    function_arns = {}
    for function_name in lambda_functions.keys():
        arn = get_stack_output(cloudformation, 'ScopeSmithLambda', f'{function_name}FunctionArn')
        if arn:
            function_arns[function_name] = arn
            print(f"Found {function_name} ARN: {arn}")
        else:
            print(f"Failed to get ARN for {function_name}")
            return

    # Create Bedrock Agent
    print("Creating Bedrock Agent...")
    agent_id = create_bedrock_agent(bedrock_agent)
    if not agent_id:
        print("Failed to create Bedrock agent")
        return

    print(f"Created Bedrock agent with ID: {agent_id}")

    # Wait for agent to be ready before creating action groups
    print("Waiting for agent to be ready...")
    agent_status = wait_for_agent_ready(bedrock_agent, agent_id)
    if not agent_status:
        print("Agent did not reach ready state in time")
        return
    
    print(f"Agent is ready with status: {agent_status}")

    # Create action groups for each Lambda function
    action_group_ids = {}
    for function_name, function_data in lambda_functions.items():
        print(f"Creating action group for {function_name}...")
        action_group_id = create_agent_action_group(
            bedrock_agent,
            agent_id,
            function_arns[function_name],
            function_name,
            function_data['description'],
            function_data['schema']
        )
        if action_group_id:
            action_group_ids[function_name] = action_group_id
            print(f"Created action group for {function_name}: {action_group_id}")
        else:
            print(f"Failed to create action group for {function_name}")

    # Prepare the agent
    print("Preparing agent...")
    status = prepare_agent(bedrock_agent, agent_id)
    if status:
        print(f"Agent preparation status: {status}")
        
        # Wait for preparation to complete
        print("Waiting for agent preparation to complete...")
        time.sleep(30)
        
        # Create agent alias
        print("Creating agent alias...")
        alias_id = create_agent_alias(bedrock_agent, agent_id)
        if alias_id:
            print(f"Created agent alias: {alias_id}")
        else:
            print("Failed to create agent alias")
    else:
        print("Failed to prepare agent")

    print("Bedrock Agent setup complete!")
    print(f"Agent ID: {agent_id}")
    print(f"Action Groups: {list(action_group_ids.keys())}")

if __name__ == "__main__":
    main()