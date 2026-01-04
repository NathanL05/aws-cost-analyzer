import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from .base_scanner import BaseScanner


class IAMScanner(BaseScanner):
    """Scanner for IAM-related security and cost issues."""
    
    def __init__(self):
        """Initialize IAM scanner (IAM is global, no region)."""
        super().__init__(region='us-east-1')
        self.iam_client = boto3.client('iam')

    def scan_unused_access_keys(self, days_threshold: int = 90, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Find IAM access keys that haven't been used recently.
        
        Unused access keys are security risks and indicate forgotten credentials.
        
        Args:
            days_threshold: Keys unused for this many days are flagged
            use_cache: If True, use cached results if available (default: True)
        
        Returns:
            List of unused access keys
        """
        cache_key = self._build_cache_key('unused_access_keys', threshold=days_threshold)
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        try:
            unused_keys = []

            paginator = self.iam_client.get_paginator('list_users')
            pages = self._retry_aws_call(
                lambda: list(paginator.paginate())
            )

            for page in pages:
                for user in page['Users']:
                    username = user['UserName']

                    try:
                        keys_response = self._retry_aws_call(
                            lambda: self.iam_client.list_access_keys(UserName=username)
                        )

                        for key_metadata in keys_response['AccessKeyMetadata']:
                            access_key_id = key_metadata['AccessKeyId']
                            create_date = key_metadata['CreateDate']

                            try:
                                last_used_response = self._retry_aws_call(
                                    lambda: self.iam_client.get_access_key_last_used(AccessKeyId=access_key_id)
                                )
                                last_used = last_used_response.get('AccessKeyLastUsed', {}).get('LastUsedDate')

                                if last_used:
                                    days_unused = (datetime.now(timezone.utc) - last_used).days
                                else:
                                    days_unused = (datetime.now(timezone.utc) - create_date).days

                                if days_unused >= days_threshold:
                                    unused_keys.append({
                                        'username': username,
                                        'access_key_id': access_key_id,
                                        'create_date': create_date.isoformat(),
                                        'last_used': last_used.isoformat() if last_used else 'Never',
                                        'days_unused': days_unused,
                                        'recommendation': f"DELETE - Unused for {days_unused} days (security risk)"
                                    })

                            except ClientError:
                                continue
                    except ClientError:
                        continue
            
            if use_cache:
                self._set_cache(cache_key, unused_keys)
            
            return unused_keys
        except ClientError as e:
            self.handle_client_error(e, "scan_unused_access_keys")
            return []