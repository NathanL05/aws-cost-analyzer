import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from datetime import datetime, timezone
class SnapshotScanner:
    def __init__(self, region: str = 'eu-west-1'):
        self.region = region 
        self.ec2_client = boto3.client('ec2', region_name=region)
    
    def scan_old_snapshots(self, age_threshold_days: int = 90) -> List[Dict[str, Any]]:
        """
        Scan for old snapshots

        Args:
            age_threshold_days: The age threshold in days for snapshots to be considered old

        Returns:
            A list of old snapshots
        """
        try: 
            pagination = self.ec2_client.get_paginator('describe_snapshots')

            old_snapshots = []
            for page in pagination.paginate(OwnerIds=['self']):
                for snapshot in page['Snapshots']:
                    snapshot_data = self._process_snapshots(snapshot, age_threshold_days)
                    if snapshot_data:
                        old_snapshots.append(snapshot_data)
            return old_snapshots

        except ClientError as e:
            print(f"Error scanning snapshots: {e}")
            return []
    
    def _process_snapshots(self, snapshot: Dict[str, Any], age_threshold_days: int) -> Dict[str, Any]:
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
            self.ec2_client.describe_volumes(VolumeIds=[volume_id])
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

