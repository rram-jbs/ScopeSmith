from typing import Any

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
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
            point_in_time_recovery=True,
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
            point_in_time_recovery=True,
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
                max_age=Duration.days(1)
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
                max_age=Duration.days(1)
            )]
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