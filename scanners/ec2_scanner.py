#!/usr/bin/env python3
"""EC2 scanner for cost leak detection."""

import boto3
from typing import List, Dict, Any
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from .base_scanner import BaseScanner


class EC2Scanner(BaseScanner):
    """Scanner for stopped EC2 instances."""
    
    def __init__(self, region: str = 'eu-west-1'):
        """Initialize the EC2 scanner."""
        super().__init__(region) 
        self.ec2_resource = boto3.resource('ec2', region_name=region)

    def scan_stopped_instances(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Scan for stopped EC2 instances with optional caching.
        
        Args:
            use_cache: If True, use cached results if available (default: True)
        
        Returns:
            List of stopped EC2 instances
        """
        cache_key = self._build_cache_key('stopped_instances')
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        try:
            paginator = self.ec2_client.get_paginator('describe_instances')
            
            stopped_instances = []
            for page in paginator.paginate(
                Filters=[{
                    'Name': 'instance-state-name',
                    'Values': ['stopped']
                }]
            ):
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        instance_data = self._process_stopped_instance(instance)
                        stopped_instances.append(instance_data)
            
            if use_cache:
                self._set_cache(cache_key, stopped_instances)
            
            return stopped_instances
        except ClientError as e:
            self.handle_client_error(e, "scan_stopped_instances")
            return []
    
    def _process_stopped_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a stopped EC2 instance (internal helper method).
        
        This is a PRIVATE method (underscore prefix) - only called by scan_stopped_instances().
        """
        instance_id = instance['InstanceId']
        instance_type = instance['InstanceType']
        launch_time = instance['LaunchTime']
        age_days = (datetime.now(timezone.utc) - launch_time).days
        ebs_cost = self._calculate_ebs_cost(instance)
        return {
            'instance_id': instance_id,
            'instance_type': instance_type,
            'state': 'stopped',
            'launch_time': launch_time.isoformat(),
            'age_days': age_days,
            'ebs_monthly_cost': ebs_cost,
            'recommendation': self._generate_recommendation(age_days, ebs_cost)
        }
    
    def _calculate_ebs_cost(self, instance: Dict[str, Any]) -> float:
        """
        Calculate monthly cost of attached EBS volumes (private helper).
        """
        total_cost = 0.0 
        for bdm in instance.get('BlockDeviceMappings', []):
            if 'Ebs' in bdm:
                volume_id = bdm['Ebs']['VolumeId']
                try:
                    volume = self.ec2_resource.Volume(volume_id)
                    price_per_gb = 0.08 if volume.volume_type == 'gp3' else 0.10
                    total_cost += price_per_gb * volume.size
                except ClientError as e:
                    self.handle_client_error(e, f"_calculate_ebs_cost (volume {volume_id})")
                    continue 
        return round(total_cost, 2)
    
    def _generate_recommendation(self, age_days: int, ebs_cost: float) -> str:
        """
        Generate recommendation based on age and EBS cost.
        """
        if age_days > 30:
            return f"TERMINATE - Stopped for {age_days} days, wasting ${ebs_cost:.2f}/month"
        elif age_days > 7:
            return f"REVIEW - Stopped for {age_days} days, costing ${ebs_cost:.2f}/month"
        else:
            return f"MONITOR - Recently stopped, costing ${ebs_cost:.2f}/month"
