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

        # Create shared Lambda layer for document processing
        document_processing_layer = lambda_.LayerVersion(
            self, "DocumentProcessingLayer",
            code=lambda_.Code.from_asset("cdk/layers/document_processing"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Common libraries for document processing (python-pptx, python-docx)"
        )

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
                metric=function.metric_errors(),
                threshold=3,
                evaluation_periods=1,
                period=Duration.minutes(5)
            )
            alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Requirements Analyzer Lambda
        self.requirements_analyzer = lambda_.Function(
            self, "RequirementsAnalyzer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda/requirements_analyzer/build"),
            handler="app.handler",
            memory_size=512,
            timeout=Duration.seconds(60),
            environment={
                **common_environment,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0"
            },
            tracing=lambda_.Tracing.ACTIVE
        )
        
        # Grant Bedrock permissions
        self.requirements_analyzer.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{self.region}:{self.account}:model/anthropic.claude-3*"]
        ))

        # Cost Calculator Lambda
        self.cost_calculator = lambda_.Function(
            self, "CostCalculator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda/cost_calculator/build"),
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
            code=lambda_.Code.from_asset("lambda/template_retriever/build"),
            handler="app.handler",
            memory_size=256,
            timeout=Duration.seconds(30),
            environment={
                **common_environment,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name
            },
            tracing=lambda_.Tracing.ACTIVE
        )

        # PowerPoint Generator Lambda with document processing layer
        self.powerpoint_generator = lambda_.Function(
            self, "PowerPointGenerator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda/powerpoint_generator/build"),
            handler="app.handler",
            memory_size=1024,
            timeout=Duration.seconds(120),
            environment={
                **common_environment,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name,
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name
            },
            layers=[document_processing_layer],
            tracing=lambda_.Tracing.ACTIVE
        )

        # SOW Generator Lambda with document processing layer
        self.sow_generator = lambda_.Function(
            self, "SOWGenerator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda/sow_generator/build"),
            handler="app.handler",
            memory_size=1024,
            timeout=Duration.seconds(120),
            environment={
                **common_environment,
                "TEMPLATES_BUCKET_NAME": infra_stack.templates_bucket.bucket_name,
                "ARTIFACTS_BUCKET_NAME": infra_stack.artifacts_bucket.bucket_name
            },
            layers=[document_processing_layer],
            tracing=lambda_.Tracing.ACTIVE
        )

        # Session Manager Lambda
        self.session_manager = lambda_.Function(
            self, "SessionManager",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda/session_manager/build"),
            handler="app.handler",
            memory_size=256,
            timeout=Duration.seconds(30),
            environment=common_environment,
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