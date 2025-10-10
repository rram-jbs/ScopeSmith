#!/usr/bin/env python3
import boto3
import json
import sys
from botocore.exceptions import ClientError
from typing import Dict, List, Any

class InfrastructureValidator:
    def __init__(self):
        self.cloudformation = boto3.client('cloudformation')
        self.dynamodb = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        self.apigateway = boto3.client('apigateway')
        self.bedrock = boto3.client('bedrock')
        
        self.validation_results = {
            'dynamodb': {'status': 'pending', 'details': []},
            's3': {'status': 'pending', 'details': []},
            'lambda': {'status': 'pending', 'details': []},
            'api': {'status': 'pending', 'details': []},
            'agentcore': {'status': 'pending', 'details': []}
        }

    def get_stack_outputs(self, stack_name: str) -> Dict[str, str]:
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            outputs = {}
            for output in response['Stacks'][0]['Outputs']:
                outputs[output['OutputKey']] = output['OutputValue']
            return outputs
        except ClientError as e:
            print(f"Error getting stack outputs for {stack_name}: {e}")
            return {}

    def validate_dynamodb(self) -> None:
        try:
            outputs = self.get_stack_outputs('ScopeSmithInfrastructure')
            tables = [
                outputs.get('SessionsTableName'),
                outputs.get('RateSheetsTableName')
            ]
            
            for table in tables:
                if table:
                    response = self.dynamodb.describe_table(TableName=table)
                    self.validation_results['dynamodb']['details'].append(
                        f"✅ Table {table} exists and is {response['Table']['TableStatus']}"
                    )
                else:
                    self.validation_results['dynamodb']['details'].append(
                        f"❌ Failed to find table name in stack outputs"
                    )
            
            self.validation_results['dynamodb']['status'] = 'success'
        except ClientError as e:
            self.validation_results['dynamodb']['status'] = 'failed'
            self.validation_results['dynamodb']['details'].append(f"❌ Error: {str(e)}")

    def validate_s3(self) -> None:
        try:
            outputs = self.get_stack_outputs('ScopeSmithInfrastructure')
            buckets = [
                outputs.get('TemplatesBucketName'),
                outputs.get('ArtifactsBucketName')
            ]
            
            for bucket in buckets:
                if bucket:
                    self.s3.head_bucket(Bucket=bucket)
                    encryption = self.s3.get_bucket_encryption(Bucket=bucket)
                    if encryption:
                        self.validation_results['s3']['details'].append(
                            f"✅ Bucket {bucket} exists and is encrypted"
                        )
                else:
                    self.validation_results['s3']['details'].append(
                        f"❌ Failed to find bucket name in stack outputs"
                    )
            
            self.validation_results['s3']['status'] = 'success'
        except ClientError as e:
            self.validation_results['s3']['status'] = 'failed'
            self.validation_results['s3']['details'].append(f"❌ Error: {str(e)}")

    def validate_lambda(self) -> None:
        try:
            outputs = self.get_stack_outputs('ScopeSmithLambda')
            function_names = [
                'RequirementsAnalyzer',
                'CostCalculator',
                'TemplateRetriever',
                'PowerPointGenerator',
                'SOWGenerator',
                'SessionManager'
            ]
            
            for function_name in function_names:
                arn = outputs.get(f'{function_name}FunctionArn')
                if arn:
                    response = self.lambda_client.get_function(FunctionName=arn)
                    self.validation_results['lambda']['details'].append(
                        f"✅ Function {function_name} exists and is {response['Configuration']['State']}"
                    )
                else:
                    self.validation_results['lambda']['details'].append(
                        f"❌ Failed to find {function_name} ARN in stack outputs"
                    )
            
            self.validation_results['lambda']['status'] = 'success'
        except ClientError as e:
            self.validation_results['lambda']['status'] = 'failed'
            self.validation_results['lambda']['details'].append(f"❌ Error: {str(e)}")

    def validate_api(self) -> None:
        try:
            outputs = self.get_stack_outputs('ScopeSmithApi')
            api_url = outputs.get('ApiUrl')
            
            if api_url:
                api_id = api_url.split('/')[-2]
                response = self.apigateway.get_rest_api(restApiId=api_id)
                self.validation_results['api']['details'].append(
                    f"✅ API {response['name']} exists and is deployed"
                )
                
                # Check API key
                keys = self.apigateway.get_api_keys()
                if keys['items']:
                    self.validation_results['api']['details'].append(
                        "✅ API key is configured"
                    )
                else:
                    self.validation_results['api']['details'].append(
                        "❌ No API key found"
                    )
            else:
                self.validation_results['api']['details'].append(
                    "❌ Failed to find API URL in stack outputs"
                )
            
            self.validation_results['api']['status'] = 'success'
        except ClientError as e:
            self.validation_results['api']['status'] = 'failed'
            self.validation_results['api']['details'].append(f"❌ Error: {str(e)}")

    def validate_agentcore(self) -> None:
        try:
            agents = self.bedrock.list_agents()
            found_agent = False
            
            for agent in agents['agentSummaries']:
                if 'ScopeSmith' in agent['agentName']:
                    found_agent = True
                    self.validation_results['agentcore']['details'].append(
                        f"✅ AgentCore agent {agent['agentName']} exists"
                    )
                    
                    # Check agent tools
                    tools = self.bedrock.list_agent_action_groups(
                        agentId=agent['agentId']
                    )
                    self.validation_results['agentcore']['details'].append(
                        f"✅ Found {len(tools['agentActionGroupSummaries'])} configured tools"
                    )
                    break
            
            if not found_agent:
                self.validation_results['agentcore']['details'].append(
                    "❌ No ScopeSmith agent found"
                )
            
            self.validation_results['agentcore']['status'] = 'success'
        except ClientError as e:
            self.validation_results['agentcore']['status'] = 'failed'
            self.validation_results['agentcore']['details'].append(f"❌ Error: {str(e)}")

    def run_validation(self) -> None:
        print("Starting infrastructure validation...")
        
        # Run all validations
        self.validate_dynamodb()
        self.validate_s3()
        self.validate_lambda()
        self.validate_api()
        self.validate_agentcore()
        
        # Print results
        print("\nValidation Results:")
        print("==================")
        
        for component, result in self.validation_results.items():
            print(f"\n{component.upper()}:")
            print("-" * (len(component) + 1))
            for detail in result['details']:
                print(detail)
        
        # Check overall status
        failed = any(r['status'] == 'failed' for r in self.validation_results.values())
        
        print("\nOverall Status:", "❌ FAILED" if failed else "✅ SUCCESS")
        if failed:
            sys.exit(1)

if __name__ == "__main__":
    validator = InfrastructureValidator()
    validator.run_validation()