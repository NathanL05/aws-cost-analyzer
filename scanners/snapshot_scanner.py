"""Snapshot scanner for cost leak detection."""

from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from .base_scanner import BaseScanner


class SnapshotScanner(BaseScanner):
    """Scanner for old EBS snapshots."""
    
    def __init__(self, region: str = 'eu-west-1'):
        """Initialize the snapshot scanner."""
        super().__init__(region)  
    
    def scan_old_snapshots(self, age_threshold_days: int = 90, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Scan for old snapshots with optional caching.

        Args:
            age_threshold_days: The age threshold in days for snapshots to be considered old
            use_cache: If True, use cached results if available (default: True)

        Returns:
            A list of old snapshots
        """
        cache_key = self._build_cache_key('old_snapshots', age_threshold=age_threshold_days)
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        try: 
            paginator = self.ec2_client.get_paginator('describe_snapshots')

            old_snapshots = []
            pages = self._retry_aws_call(
                lambda: list(paginator.paginate(OwnerIds=['self']))
            )
            for page in pages:
                for snapshot in page['Snapshots']:
                    snapshot_data = self._process_snapshots(snapshot, age_threshold_days)
                    if snapshot_data:
                        old_snapshots.append(snapshot_data)
            
            if use_cache:
                self._set_cache(cache_key, old_snapshots)
            
            return old_snapshots

        except ClientError as e:
            self.handle_client_error(e, "scan_old_snapshots")
            return []
    
    def _process_snapshots(self, snapshot: Dict[str, Any], age_threshold_days: int) -> Optional[Dict[str, Any]]:
        """
        Process a snapshot and return the data
        """
        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot['VolumeId']
        size_gb = snapshot['VolumeSize']
        start_time = snapshot['StartTime']

        age_days = (datetime.now(timezone.utc) - start_time).days

        if age_days < age_threshold_days:
            return None 
        
        monthly_cost = round(size_gb * 0.05, 2)
        volume_exists = self._check_volume_exists(volume_id) 

        return {
            'snapshot_id': snapshot_id,
            'volume_id': volume_id,
            'start_time': start_time,
            'size_gb': size_gb,
            'age_days': age_days,
            'monthly_cost': monthly_cost,
            'volume_exists': volume_exists,
            'recommendation': self._generate_recommendation(age_days, monthly_cost, volume_exists)
        }
        
    def _check_volume_exists(self, volume_id: str) -> bool:
        """
        Check if a volume exists
        """
        if volume_id == "unknown":
            return False
        try:
            self._retry_aws_call(
                lambda: self.ec2_client.describe_volumes(VolumeIds=[volume_id])
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                return False
            raise 
    
    def _generate_recommendation(self, age_days: int, cost: float, volume_exists: bool) -> str:
        """
        Generate a recommendation for the snapshot
        """
        if age_days > 180 and not volume_exists:
            return f"DELETE - Orphaned snapshot (volume gone), {age_days} days old, ${cost:.2f}/month"
        elif age_days > 180:
            return f"REVIEW - Very old ({age_days} days), ${cost:.2f}/month"
        else:
            return f"MONITOR - Old snapshot ({age_days} days), ${cost:.2f}/month"

