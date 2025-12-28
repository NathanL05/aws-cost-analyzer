"""Tests for EC2 scanner."""

from unittest.mock import patch, Mock
from datetime import datetime, timezone
from scanners.ec2_scanner import EC2Scanner
import botocore.client


def test_ec2_scanner_initialization():
    """Test EC2Scanner initialization."""
    scanner = EC2Scanner()
    
    assert scanner.region == 'eu-west-1'
    
    assert isinstance(scanner.ec2_client, botocore.client.BaseClient)
    
    assert scanner.ec2_resource is not None
    assert hasattr(scanner.ec2_resource, 'meta') 


@patch('boto3.resource')
@patch('boto3.client')
def test_scan_stopped_instances(mock_boto_client, mock_boto_resource):
    """Test scanning stopped instances method."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    mock_volume = Mock()
    mock_volume.size = 100 
    mock_volume.volume_type = 'gp2'  
    mock_resource.Volume.return_value = mock_volume
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    launch_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    mock_paginator.paginate.return_value = [{
        'Reservations': [
            {
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'InstanceType': 't2.micro',  
                    'State': {
                        'Name': 'stopped'
                    },
                    'LaunchTime': launch_time,  
                    'BlockDeviceMappings': [
                        {
                            'Ebs': {
                                'VolumeId': 'vol-1234567890abcdef0'
                            }
                        }
                    ]
                }]
            }
        ]
    }]
    
    scanner = EC2Scanner()
    stopped_instances = scanner.scan_stopped_instances()
    
    assert len(stopped_instances) == 1
    assert stopped_instances[0]['instance_id'] == 'i-1234567890abcdef0'
    assert stopped_instances[0]['instance_type'] == 't2.micro'
    assert stopped_instances[0]['state'] == 'stopped'
    assert stopped_instances[0]['launch_time'] == launch_time.isoformat()
    assert stopped_instances[0]['ebs_monthly_cost'] == 10.0  
    assert 'TERMINATE' in stopped_instances[0]['recommendation'] or 'MONITOR' in stopped_instances[0]['recommendation']