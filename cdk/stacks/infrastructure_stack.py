from typing import Any

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
)
from constructs import Construct

class InfrastructureStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create DynamoDB Tables
        self.sessions_table = dynamodb.Table(
            self, "SessionsTable",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl"
        )

        self.rate_sheets_table = dynamodb.Table(
            self, "RateSheetsTable",
            partition_key=dynamodb.Attribute(
                name="role_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.RETAIN
        )

        # Create S3 Buckets
        self.templates_bucket = s3.Bucket(
            self, "TemplatesBucket",
            bucket_name=f"scopesmith-templates-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT],
                allowed_origins=["*"],
                allowed_headers=["*"],
                max_age=86400  # 1 day in seconds
            )]
        )

        self.artifacts_bucket = s3.Bucket(
            self, "ArtifactsBucket",
            bucket_name=f"scopesmith-artifacts-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(30)
                )
            ],
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT],
                allowed_origins=["*"],
                allowed_headers=["*"],
                max_age=86400  # 1 day in seconds
            )]
        )

        # Create IAM Role for Bedrock Agent
        self.bedrock_agent_role = iam.Role(
            self, "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ],
            inline_policies={
                "BedrockAgentPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                                "bedrock:GetFoundationModel",
                                "bedrock:ListFoundationModels"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::scopesmith-templates-{self.account}-{self.region}",
                                f"arn:aws:s3:::scopesmith-templates-{self.account}-{self.region}/*",
                                f"arn:aws:s3:::scopesmith-artifacts-{self.account}-{self.region}",
                                f"arn:aws:s3:::scopesmith-artifacts-{self.account}-{self.region}/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                                "dynamodb:Scan"
                            ],
                            resources=[
                                self.sessions_table.table_arn,
                                self.rate_sheets_table.table_arn
                            ]
                        )
                    ]
                )
            }
        )

        # CloudFormation Outputs
        CfnOutput(self, "SessionsTableName",
            value=self.sessions_table.table_name,
            description="DynamoDB Sessions Table Name",
            export_name="ScopeSmithSessionsTableName"
        )

        CfnOutput(self, "RateSheetsTableName",
            value=self.rate_sheets_table.table_name,
            description="DynamoDB Rate Sheets Table Name",
            export_name="ScopeSmithRateSheetsTableName"
        )

        CfnOutput(self, "TemplatesBucketName",
            value=self.templates_bucket.bucket_name,
            description="Templates S3 Bucket Name",
            export_name="ScopeSmithTemplatesBucketName"
        )

        CfnOutput(self, "ArtifactsBucketName",
            value=self.artifacts_bucket.bucket_name,
            description="Artifacts S3 Bucket Name",
            export_name="ScopeSmithArtifactsBucketName"
        )

        CfnOutput(self, "BedrockAgentRoleArn",
            value=self.bedrock_agent_role.role_arn,
            description="Bedrock Agent IAM Role ARN",
            export_name="ScopeSmithBedrockAgentRoleArn"
        )