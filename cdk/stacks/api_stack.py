from typing import Any

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    aws_apigateway as apigateway,
    aws_iam as iam,
)
from constructs import Construct
from .lambda_stack import LambdaStack

class ApiStack(Stack):
    def __init__(self, scope: Construct, id: str, lambda_stack: LambdaStack, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create REST API
        api = apigateway.RestApi(
            self, "ScopeSmithApi",
            rest_api_name="ScopeSmith API",
            description="API for ScopeSmith proposal generation system",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type", 
                    "X-Amz-Date", 
                    "Authorization", 
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                    "X-Amz-User-Agent"
                ],
                allow_credentials=False
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            )
        )

        # Create API usage plan and key
        plan = api.add_usage_plan("ScopeSmithUsagePlan",
            name="Basic",
            throttle=apigateway.ThrottleSettings(
                rate_limit=10,
                burst_limit=20
            )
        )
        key = api.add_api_key("ScopeSmithApiKey")
        plan.add_api_key(key)

        # Create API resources
        api_resource = api.root.add_resource("api")

        # POST /api/submit-assessment
        assessment_resource = api_resource.add_resource("submit-assessment")
        assessment_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                lambda_stack.session_manager,
                proxy=True,
                timeout=Duration.seconds(29)  # API Gateway max timeout, Lambda returns quickly
            ),
            api_key_required=False
        )

        # GET /api/agent-status/{session_id}
        status_resource = api_resource.add_resource("agent-status").add_resource("{session_id}")
        status_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(
                lambda_stack.session_manager,
                proxy=True,
                timeout=Duration.seconds(29)  # Fast polling endpoint
            ),
            api_key_required=False
        )

        # GET /api/results/{session_id}
        results_resource = api_resource.add_resource("results").add_resource("{session_id}")
        results_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(
                lambda_stack.session_manager,
                proxy=True,
                timeout=Duration.seconds(29)
            ),
            api_key_required=False
        )

        # POST /api/upload-template
        upload_resource = api_resource.add_resource("upload-template")
        upload_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                lambda_stack.template_retriever,
                proxy=True
            ),
            api_key_required=False
        )

        # Create request validator
        api.add_request_validator("DefaultValidator",
            validate_request_body=True,
            validate_request_parameters=True
        )

        # Add model schemas for request validation
        api.add_model("SubmitAssessmentRequest",
            content_type="application/json",
            model_name="SubmitAssessmentRequest",
            schema=apigateway.JsonSchema(
                type=apigateway.JsonSchemaType.OBJECT,
                required=["client_name", "requirements"],
                properties={
                    "client_name": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "requirements": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
                }
            )
        )

        # CloudFormation outputs
        CfnOutput(self, "ApiUrl",
            value=api.url,
            description="ScopeSmith API URL",
            export_name="ScopeSmithApiUrl"
        )
        
        CfnOutput(self, "ApiKey",
            value=key.key_id,
            description="ScopeSmith API Key ID",
            export_name="ScopeSmithApiKeyId"
        )