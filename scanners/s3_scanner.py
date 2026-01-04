"""S3 scanner for cost leak detection."""

import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from .base_scanner import BaseScanner


class S3Scanner(BaseScanner):
    """Scanner for S3-related cost leaks."""
    
    def __init__(self) -> None:
        """Initialize S3 scanner (S3 is global, no region needed)."""
        super().__init__(region='us-east-1')
        self.s3_client = boto3.client('s3')

    def scan_unused_buckets(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Find S3 buckets that are empty or have no recent activity.
        
        Empty buckets still cost $0.023/GB-month (minimal but accumulates).
        Unused buckets indicate forgotten resources. 

        Args:
            use_cache: If True, use cached results if available (default: True)

        Returns:
            List of unused/empty buckets. 
        """
        cache_key = self._build_cache_key('unused_buckets')
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        try:
            response = self._retry_aws_call(
                lambda: self.s3_client.list_buckets()
            )
            unused_buckets = []

            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                creation_date = bucket['CreationDate']
                
                try:
                    objects = self._retry_aws_call(
                        lambda: self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                    )
                    is_empty = 'Contents' not in objects or len(objects.get('Contents', [])) == 0
                except ClientError:
                    is_empty = False  

                age_days = (datetime.now(timezone.utc) - creation_date).days
                
                monthly_cost = 0.01 

                if is_empty or age_days > 90:
                    unused_buckets.append({
                        'bucket_name': bucket_name,
                        'creation_date': creation_date.isoformat(),
                        'age_days': age_days,
                        'is_empty': is_empty,
                        'monthly_cost': monthly_cost,
                        'recommendation': self._generate_recommendation(is_empty, age_days)
                    })
            
            if use_cache:
                self._set_cache(cache_key, unused_buckets)
            
            return unused_buckets

        except ClientError as e:
            self.handle_client_error(e, "scan_unused_buckets")
            return []
    
    def _generate_recommendation(self, is_empty: bool, age_days: int) -> str:
        """
        Generate a recommendation based on bucket state.
        """
        if is_empty and age_days > 30:
            return f"DELETE - Empty bucket, {age_days} days old"
        elif age_days > 180:
            return f"REVIEW - Bucket {age_days} days old, check if still needed"
        else:
            return "MONITOR - Recently created or has content"

