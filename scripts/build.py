#!/usr/bin/env python3
import os
import shutil
import subprocess
from pathlib import Path

def create_lambda_layer(name: str, requirements_file: str) -> None:
    """Create a Lambda layer for shared dependencies."""
    print(f"Creating Lambda layer: {name}")
    layer_dir = Path("cdk") / "layers" / name / "python"
    layer_dir.mkdir(parents=True, exist_ok=True)
    
    # Install dependencies into layer directory
    subprocess.run([
        "pip", "install",
        "-r", requirements_file,
        "-t", str(layer_dir),
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", "3.12",
        "--only-binary=:all:"
    ], check=True)

def package_lambda_function(function_dir: str) -> None:
    """Package a Lambda function with its dependencies."""
    print(f"Packaging Lambda function: {function_dir}")
    requirements_file = os.path.join(function_dir, "requirements.txt")
    
    if os.path.exists(requirements_file):
        # Create a temporary directory for dependencies
        build_dir = os.path.join(function_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        # Install dependencies
        subprocess.run([
            "pip", "install",
            "-r", requirements_file,
            "-t", build_dir,
            "--platform", "manylinux2014_x86_64",
            "--implementation", "cp",
            "--python-version", "3.12",
            "--only-binary=:all:"
        ], check=True)
        
        # Copy function code
        shutil.copy2(
            os.path.join(function_dir, "app.py"),
            os.path.join(build_dir, "app.py")
        )

def main():
    # Create build directories
    os.makedirs("cdk/layers", exist_ok=True)
    
    # Package each Lambda function
    lambda_functions = [
        "requirements_analyzer",
        "cost_calculator",
        "template_retriever",
        "powerpoint_generator",
        "sow_generator",
        "session_manager"
    ]
    
    for function in lambda_functions:
        function_dir = os.path.join("lambda", function)
        package_lambda_function(function_dir)
    
    # Create common layers
    create_lambda_layer(
        "document_processing",
        "scripts/requirements.txt"  # Contains python-pptx and python-docx
    )
    
    print("\nBuild completed successfully!")
    print("Run 'cdk deploy --all' to deploy the infrastructure")

if __name__ == "__main__":
    main()