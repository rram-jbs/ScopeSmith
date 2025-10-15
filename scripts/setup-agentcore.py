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

def update_session_manager_environment(lambda_client, function_name, agent_id, alias_id):
    """Update the session manager Lambda function with Bedrock Agent details"""
    try:
        # Get current function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Update with Bedrock Agent details
        current_env['BEDROCK_AGENT_ID'] = agent_id
        current_env['BEDROCK_AGENT_ALIAS_ID'] = alias_id
        
        # Update the function
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': current_env}
        )
        
        print(f"Updated {function_name} with Agent ID: {agent_id} and Alias ID: {alias_id}")
        return True
        
    except ClientError as e:
        print(f"Error updating session manager environment: {e}")
        return False

def grant_lambda_bedrock_permissions(iam_client, lambda_client, function_name, agent_id, alias_id):
    """Grant the session manager Lambda function permissions to invoke the Bedrock Agent"""
    try:
        # Get the Lambda function's role
        response = lambda_client.get_function(FunctionName=function_name)
        role_arn = response['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        
        # Create policy document for Bedrock Agent access
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeAgent"
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:*:*:agent/{agent_id}",
                        f"arn:aws:bedrock:*:*:agent-alias/{agent_id}/{alias_id}"
                    ]
                }
            ]
        }
        
        # Attach inline policy to the role
        policy_name = f"BedrockAgent-{agent_id}-Access"
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"Granted Bedrock Agent permissions to {function_name}")
        return True
        
    except ClientError as e:
        print(f"Error granting Bedrock permissions: {e}")
        return False

def grant_agent_lambda_permissions(lambda_client, agent_id, function_arns):
    """Grant the Bedrock Agent permissions to invoke Lambda functions"""
    try:
        for function_name, function_arn in function_arns.items():
            try:
                # Add permission for Bedrock Agent to invoke the Lambda function
                lambda_client.add_permission(
                    FunctionName=function_arn,
                    StatementId=f"bedrock-agent-{agent_id}-invoke-{function_name}",
                    Action='lambda:InvokeFunction',
                    Principal='bedrock.amazonaws.com',
                    SourceArn=f'arn:aws:bedrock:*:*:agent/{agent_id}'
                )
                print(f"Granted invoke permission for {function_name} to Bedrock Agent")
            except ClientError as e:
                if "ResourceConflictException" in str(e):
                    print(f"Permission already exists for {function_name}")
                else:
                    print(f"Error granting permission for {function_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error granting agent Lambda permissions: {e}")
        return False

def create_bedrock_agent(bedrock_agent, agent_role_arn, agent_instruction):
    """Create a Bedrock Agent for ScopeSmith"""
    try:
        agent_response = bedrock_agent.create_agent(
            agentName="ScopeSmithAgent",
            description="AI agent for analyzing project requirements and generating scopes of work",
            agentResourceRoleArn=agent_role_arn,  # Fixed: changed from roleArn to agentResourceRoleArn
            foundationModel="us.anthropic.claude-3-5-sonnet-20241022-v2:0",  # Using inference profile
            instruction=agent_instruction,
            idleSessionTTLInSeconds=1800  # 30 minutes
        )
        return agent_response['agent']['agentId']
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
    lambda_client = boto3.client('lambda')
    iam_client = boto3.client('iam')

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

    # Get Session Manager ARN
    session_manager_arn = get_stack_output(cloudformation, 'ScopeSmithLambda', 'SessionManagerFunctionArn')
    if not session_manager_arn:
        print("Failed to get Session Manager ARN")
        return

    # Define agent role ARN and instruction
    agent_role_arn = "arn:aws:iam::123456789012:role/ScopeSmithAgentRole"
    agent_instruction = """You are ScopeSmith, an AI assistant specialized in generating professional proposals and statements of work. 
    You help analyze client requirements, calculate costs, and generate comprehensive proposals with PowerPoint presentations and SOW documents.
    
    Your capabilities include:
    - Analyzing client requirements and breaking them down into deliverables
    - Calculating project costs based on standard rate sheets
    - Retrieving appropriate document templates
    - Generating customized PowerPoint presentations
    - Creating detailed Statements of Work
    
    Always maintain a professional tone and ensure all outputs are well-structured and comprehensive."""

    # Create Bedrock Agent
    print("Creating Bedrock Agent...")
    agent_id = create_bedrock_agent(bedrock_agent, agent_role_arn, agent_instruction)
    if not agent_id:
        print("Failed to create Bedrock agent")
        return

    print(f"Created Bedrock agent with ID: {agent_id}")

    # Grant Lambda functions permission for Bedrock Agent to invoke them
    print("Granting Bedrock Agent permissions to invoke Lambda functions...")
    grant_agent_lambda_permissions(lambda_client, agent_id, function_arns)

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
            
            # Update Session Manager with Agent details
            print("Updating Session Manager with Bedrock Agent details...")
            session_manager_function_name = session_manager_arn.split(':')[-1]
            
            if update_session_manager_environment(lambda_client, session_manager_function_name, agent_id, alias_id):
                print("Successfully updated Session Manager environment variables")
                
                # Grant Session Manager permissions to invoke Bedrock Agent
                print("Granting Session Manager permissions to invoke Bedrock Agent...")
                grant_lambda_bedrock_permissions(iam_client, lambda_client, session_manager_function_name, agent_id, alias_id)
                
                print("🎉 Phase 2 AgentCore setup complete!")
                print(f"✅ Agent ID: {agent_id}")
                print(f"✅ Agent Alias ID: {alias_id}")
                print(f"✅ Action Groups: {list(action_group_ids.keys())}")
                print(f"✅ Session Manager updated with AgentCore configuration")
                print("\n🚀 Your system is now using AI-orchestrated AgentCore approach!")
                
            else:
                print("Failed to update Session Manager environment")
        else:
            print("Failed to create agent alias")
    else:
        print("Failed to prepare agent")

if __name__ == "__main__":
    main()