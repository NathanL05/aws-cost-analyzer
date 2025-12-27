import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from datetime import datetime, timezone


class EBSScanner:
    def __init__(self, region: str = "eu-west-1"):
        """
        Initialize the EBSScanner.
        """
        self.region = region
        self.ec2_client = boto3.client("ec2", region_name=region)
    

    def scan_unattached_volumes(self) -> List[Dict[str, Any]]:
        """
        Scan for unattached EBS volumes.
        """
        try:
            response = self.ec2_client.get_paginator('describe_volumes')
            unattached_volumes = []
            for page in response.paginate():
                for volume in page.get('Volumes', []):
                    if volume.get('State') == 'available':
                        volume_data = self._process_unattached_volume(volume)
                        unattached_volumes.append(volume_data)
            return unattached_volumes
        except ClientError as e:
            print(f"Error scanning unattached volumes: {e}")
            return []
    def _process_unattached_volume(self, volume: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an unattached EBS volume.
        """
        
        volume_id = volume.get('VolumeId')
        size = volume.get('Size')
        volume_type = volume.get('VolumeType')
        availability_zone = volume.get('AvailabilityZone')
        create_time = volume.get('CreateTime')
        age_days = (datetime.now(timezone.utc) - volume.get('CreateTime')).days
        monthly_cost = self._calculate_monthly_cost(size, volume_type)
        recommendation = self._generate_recommendation(age_days, monthly_cost)

        return {
            'volume_id': volume_id,
            'size': size,
            'volume_type': volume_type,
            'create_time': create_time,
            'availability_zone': availability_zone,
            'age_days': age_days,
            'recommendation': recommendation,
            'monthly_cost': monthly_cost
        }
    
    def _calculate_monthly_cost(self, size_gb: int,volume_type: str) -> float:
        """
        Calculate the monthly cost of an unattached EBS volume.
        """

        pricing = {
            'gp3': 0.08,  
            'gp2': 0.10,   
            'io1': 0.125,  
            'io2': 0.125,
            'st1': 0.045,  
            'sc1': 0.015,  
            'standard': 0.05  
        }
        price_per_gb = pricing.get(volume_type, 0.10)
        return round(size_gb * price_per_gb, 2)

    def _generate_recommendation(self, age_days: int, cost: float) -> str:
        """
        Generate a recommendation for an unattached EBS volume.
        """
        if age_days > 30:
            return f"DELETE - Unattached for {age_days} days, wasting ${cost:.2f}/month"
        elif age_days > 7:
            return f"REVIEW - Unattached for {age_days} days, costing ${cost:.2f}/month"
        else:
            return f"MONITOR - Recently detached, costing ${cost:.2f}/month"
