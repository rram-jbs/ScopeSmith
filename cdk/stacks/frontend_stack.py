from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
)
from constructs import Construct
from .api_stack import ApiStack

class FrontendStack(Stack):
    def __init__(self, scope: Construct, id: str, api_stack: ApiStack, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create S3 bucket for static hosting
        frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            bucket_name=f"scopesmith-frontend-{self.account}-{self.region}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False
        )

        # Create Origin Access Identity for CloudFront
        origin_identity = cloudfront.OriginAccessIdentity(
            self, "OriginAccessIdentity",
            comment="Access identity for ScopeSmith frontend"
        )

        # Grant read access to CloudFront
        frontend_bucket.grant_read(origin_identity)

        # Create CloudFront distribution
        distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    frontend_bucket,
                    origin_access_identity=origin_identity
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html"
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html"
                )
            ]
        )

        # CloudFormation outputs
        CfnOutput(self, "FrontendBucketName",
            value=frontend_bucket.bucket_name,
            description="Frontend S3 Bucket Name",
            export_name="ScopeSmithFrontendBucketName"
        )

        CfnOutput(self, "CloudFrontDomainName",
            value=distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
            export_name="ScopeSmithCloudFrontDomainName"
        )

        CfnOutput(self, "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="CloudFront Distribution ID",
            export_name="ScopeSmithCloudFrontDistributionId"
        )