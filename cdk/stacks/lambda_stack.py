from typing import Any

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
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

        # Create alarm topic for Lambda errors
        alarm_topic = sns.Topic(self, "LambdaErrorAlarmTopic")

        # Helper method to create CloudWatch alarm
        def create_error_alarm(function: lambda_.Function, function_name: str):
            alarm = cloudwatch.Alarm(
                self, f"{function_name}ErrorAlarm",
                metric=function.metric_errors(
                    period=Duration.minutes(5)
                ),
                threshold=3,
                evaluation_periods=1
            )
            alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

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
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0"
            },
            tracing=lambda_.Tracing.ACTIVE
        )
        
        # Grant Bedrock permissions - foundation models don't include account ID
        self.requirements_analyzer.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3*"
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
                "RATE_SHEETS_TABLE_NAME": infra_stack.rate_sheets_table.table_name
            },
            tracing=lambda_.Tracing.ACTIVE
        )

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
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name
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
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name
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
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name
            },
            tracing=lambda_.Tracing.ACTIVE
        )

        # Session Manager Lambda - Updated for Phase 2 AgentCore support
        self.session_manager = lambda_.Function(
            self, "SessionManager",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("../lambda/session_manager"),
            handler="app.handler",
            memory_size=256,
            timeout=Duration.seconds(30),
            environment={
                **common_environment,
                # Phase 1 fallback environment variables
                "REQUIREMENTS_ANALYZER_ARN": self.requirements_analyzer.function_arn,
                "COST_CALCULATOR_ARN": self.cost_calculator.function_arn,
                "TEMPLATE_RETRIEVER_ARN": self.template_retriever.function_arn,
                "POWERPOINT_GENERATOR_ARN": self.powerpoint_generator.function_arn,
                "SOW_GENERATOR_ARN": self.sow_generator.function_arn,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name,
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name,
                # Phase 2 AgentCore environment variables (will be set by setup script)
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
        for func in [self.template_retriever, self.powerpoint_generator, self.sow_generator]:
            infra_stack.templates_bucket.grant_read(func)
            infra_stack.artifacts_bucket.grant_read_write(func)

        # Grant session manager permission to invoke other Lambda functions (Phase 1 fallback)
        self.session_manager.add_to_role_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=[
                self.requirements_analyzer.function_arn,
                self.cost_calculator.function_arn,
                self.template_retriever.function_arn,
                self.powerpoint_generator.function_arn,
                self.sow_generator.function_arn
            ]
        ))

        # Grant session manager Bedrock Agent permissions (Phase 2)
        self.session_manager.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeAgent",
                "bedrock:GetAgent",
                "bedrock:ListAgents"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
                f"arn:aws:bedrock:{self.region}:{self.account}:agent-alias/*"
            ]
        ))

        # Grant requirements analyzer permission to invoke cost calculator
        self.requirements_analyzer.add_to_role_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=[self.cost_calculator.function_arn]
        ))

        # Add cost calculator ARN to requirements analyzer environment
        self.requirements_analyzer.add_environment("COST_CALCULATOR_ARN", self.cost_calculator.function_arn)

        # Grant cost calculator permission to invoke template retriever
        self.cost_calculator.add_to_role_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=[self.template_retriever.function_arn]
        ))

        # Add template retriever ARN to cost calculator environment
        self.cost_calculator.add_environment("TEMPLATE_RETRIEVER_ARN", self.template_retriever.function_arn)

        # Create CloudWatch alarms for all functions
        for func, name in [
            (self.requirements_analyzer, "RequirementsAnalyzer"),
            (self.cost_calculator, "CostCalculator"),
            (self.template_retriever, "TemplateRetriever"),
            (self.powerpoint_generator, "PowerPointGenerator"),
            (self.sow_generator, "SOWGenerator"),
            (self.session_manager, "SessionManager")
        ]:
            create_error_alarm(func, name)

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