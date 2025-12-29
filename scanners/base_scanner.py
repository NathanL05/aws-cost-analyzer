"""Base scanner with common functionality."""

import boto3
from typing import Dict, Any
from botocore.exceptions import ClientError


class BaseScanner:
    """Base class for all resource scanners."""
    
    def __init__(self, region: str = 'eu-west-1'):
        """Initialize scanner with region."""
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)
    
    def handle_client_error(self, error: ClientError, context: str) -> None:
        """Standard error handling for boto3 ClientError."""
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        print(f"Error in {context}: [{error_code}] {error_message}")