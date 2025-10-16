from typing import Any

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_lambda as lambda_,
    aws_iam as iam,
)
from constructs import Construct
from .infrastructure_stack import InfrastructureStack

class LambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, infra_stack: InfrastructureStack, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Common Lambda configurations
        common_environment = {
            "AWS_LAMBDA_FUNCTION_TIMEOUT": "60",
            "SESSIONS_TABLE_NAME": infra_stack.sessions_table.table_name,
        }

        # Requirements Analyzer Lambda
        self.requirements_analyzer = lambda_.Function(
            self, "RequirementsAnalyzer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("../lambda/requirements_analyzer"),
            handler="app.handler",
            memory_size=512,
            timeout=Duration.seconds(60),
            environment={
                **common_environment,
                "BEDROCK_MODEL_ID": "amazon.nova-pro-v1:0",  # Using Amazon Nova Pro for higher rate limits
            },
            tracing=lambda_.Tracing.ACTIVE
        )
        
        # Grant Bedrock permissions for Amazon Nova Pro
        self.requirements_analyzer.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-pro-v1:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-*"
            ]
        ))

        # Cost Calculator Lambda
        self.cost_calculator = lambda_.Function(
            self, "CostCalculator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("../lambda/cost_calculator"),
            handler="app.handler",
            memory_size=256,
            timeout=Duration.seconds(30),
            environment={
                **common_environment,
                "RATE_SHEETS_TABLE_NAME": infra_stack.rate_sheets_table.table_name,
                "BEDROCK_MODEL_ID": "amazon.nova-pro-v1:0"  # Changed from Claude to Nova Pro
            },
            tracing=lambda_.Tracing.ACTIVE
        )
        
        # Grant Bedrock permissions to Cost Calculator
        self.cost_calculator.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-pro-v1:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-*"
            ]
        ))

        # Template Retriever Lambda
        self.template_retriever = lambda_.Function(
            self, "TemplateRetriever",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("../lambda/template_retriever"),
            handler="app.handler",
            memory_size=256,
            timeout=Duration.seconds(30),
            environment={
                **common_environment,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name,
                "TEMPLATE_BUCKET_NAME": infra_stack.templates_bucket.bucket_name
            },
            tracing=lambda_.Tracing.ACTIVE
        )

        # PowerPoint Generator Lambda
        self.powerpoint_generator = lambda_.Function(
            self, "PowerPointGenerator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("../lambda/powerpoint_generator"),
            handler="app.handler",
            memory_size=1024,
            timeout=Duration.seconds(120),
            environment={
                **common_environment,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name,
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name,
                "BEDROCK_MODEL_ID": "amazon.nova-pro-v1:0"  # For AI content generation
            },
            tracing=lambda_.Tracing.ACTIVE
        )

        # SOW Generator Lambda
        self.sow_generator = lambda_.Function(
            self, "SOWGenerator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("../lambda/sow_generator"),
            handler="app.handler",
            memory_size=1024,
            timeout=Duration.seconds(120),
            environment={
                **common_environment,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name,
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name,
                "BEDROCK_MODEL_ID": "amazon.nova-pro-v1:0"  # For AI content generation
            },
            tracing=lambda_.Tracing.ACTIVE
        )

        # Session Manager Lambda - AgentCore Runtime only
        self.session_manager = lambda_.Function(
            self, "SessionManager",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("../lambda/session_manager"),
            handler="app.handler",
            memory_size=256,
            timeout=Duration.seconds(900),  # 15 minutes for async agent workflow processing
            environment={
                **common_environment,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name,
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name,
                "AGENTCORE_RUNTIME_ARN": "PLACEHOLDER_RUNTIME_ARN",
                "AGENTCORE_RUNTIME_ID": "PLACEHOLDER_RUNTIME_ID",
                "BEDROCK_AGENT_ID": "PLACEHOLDER_AGENT_ID",
                "BEDROCK_AGENT_ALIAS_ID": "PLACEHOLDER_ALIAS_ID"
            },
            tracing=lambda_.Tracing.ACTIVE
        )

        # Grant DynamoDB permissions
        infra_stack.sessions_table.grant_read_write_data(self.session_manager)
        infra_stack.sessions_table.grant_read_write_data(self.requirements_analyzer)
        infra_stack.sessions_table.grant_read_write_data(self.cost_calculator)
        infra_stack.sessions_table.grant_read_write_data(self.template_retriever)
        infra_stack.sessions_table.grant_read_write_data(self.powerpoint_generator)
        infra_stack.sessions_table.grant_read_write_data(self.sow_generator)
        infra_stack.rate_sheets_table.grant_read_data(self.cost_calculator)

        # Grant S3 permissions
        for func in [self.template_retriever, self.powerpoint_generator, self.sow_generator, self.session_manager]:
            infra_stack.templates_bucket.grant_read(func)
            infra_stack.artifacts_bucket.grant_read_write(func)

        # Grant session manager permission to invoke itself asynchronously (using wildcard to avoid circular dependency)
        self.session_manager.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "lambda:InvokeFunction",
                "lambda:InvokeAsync"
            ],
            resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:*SessionManager*"]
        ))

        # Grant session manager AgentCore Runtime permissions
        self.session_manager.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeAgentRuntime",
                "bedrock:GetAgentRuntime",
                "bedrock:ListAgentRuntimes"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}:{self.account}:agent-runtime/*"
            ]
        ))

        # Grant session manager Bedrock Agent permissions
        self.session_manager.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeAgent",
                "bedrock:GetAgent",
                "bedrock:ListAgents",
                "bedrock:InvokeAgentRuntime"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
                f"arn:aws:bedrock:{self.region}:{self.account}:agent-alias/*/*"
            ]
        ))
        
        # Grant Bedrock permissions to PowerPoint and SOW generators for content generation
        for func in [self.powerpoint_generator, self.sow_generator]:
            func.add_to_role_policy(iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-pro-v1:0",
                    f"arn:aws:bedrock::{self.region}::foundation-model/amazon.nova-*"
                ]
            ))

        # Grant Bedrock service permission to invoke all Lambda functions (for AgentCore Gateway)
        for func in [self.requirements_analyzer, self.cost_calculator, self.template_retriever, 
                     self.powerpoint_generator, self.sow_generator]:
            func.add_permission(
                "BedrockInvokePermission",
                principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
                action="lambda:InvokeFunction"
            )

        # CloudFormation outputs
        for func, name in [
            (self.requirements_analyzer, "RequirementsAnalyzer"),
            (self.cost_calculator, "CostCalculator"),
            (self.template_retriever, "TemplateRetriever"),
            (self.powerpoint_generator, "PowerPointGenerator"),
            (self.sow_generator, "SOWGenerator"),
            (self.session_manager, "SessionManager")
        ]:
            CfnOutput(self, f"{name}FunctionArn",
                value=func.function_arn,
                description=f"{name} Lambda Function ARN",
                export_name=f"ScopeSmith{name}FunctionArn"
            )