#!/usr/bin/env python3
from aws_cdk import App, Environment, Tags
from stacks.infrastructure_stack import InfrastructureStack
from stacks.lambda_stack import LambdaStack
from stacks.api_stack import ApiStack
from stacks.frontend_stack import FrontendStack

app = App()

# Define environment
env = Environment(
    account=app.account,
    region=app.region or "us-east-1"
)

# Create stacks with dependencies
infra_stack = InfrastructureStack(app, "ScopeSmithInfrastructure", env=env)
lambda_stack = LambdaStack(app, "ScopeSmithLambda", infra_stack=infra_stack, env=env)
api_stack = ApiStack(app, "ScopeSmithApi", lambda_stack=lambda_stack, env=env)
frontend_stack = FrontendStack(app, "ScopeSmithFrontend", api_stack=api_stack, env=env)

# Add common tags to all resources
for stack in [infra_stack, lambda_stack, api_stack, frontend_stack]:
    Tags.of(stack).add("Project", "ScopeSmith")
    Tags.of(stack).add("Environment", "dev")
    Tags.of(stack).add("Hackathon", "AWS-AI-Agent")

app.synth()