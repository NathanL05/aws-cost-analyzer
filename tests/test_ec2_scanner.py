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


@patch('boto3.resource')
@patch('boto3.client')
def test_scan_stopped_instances_error_handling(mock_boto_client, mock_boto_resource):
    """Test error handling when AWS API fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    from botocore.exceptions import ClientError
    mock_paginator.paginate.side_effect = ClientError(
        {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'You are not authorized'}},
        'describe_instances'
    )
    
    scanner = EC2Scanner()
    stopped_instances = scanner.scan_stopped_instances()
    
    assert isinstance(stopped_instances, list)
    assert stopped_instances == []


@patch('boto3.resource')
@patch('boto3.client')
def test_scan_stopped_instances_no_ebs_volumes(mock_boto_client, mock_boto_resource):
    """Test instance without EBS volumes."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    launch_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    mock_paginator.paginate.return_value = [{
        'Reservations': [
            {
                'Instances': [{
                    'InstanceId': 'i-no-ebs-volume',
                    'InstanceType': 't2.micro',
                    'State': {
                        'Name': 'stopped'
                    },
                    'LaunchTime': launch_time,
                    'BlockDeviceMappings': []  
                }]
            }
        ]
    }]
    
    scanner = EC2Scanner()
    stopped_instances = scanner.scan_stopped_instances()
    
    assert len(stopped_instances) == 1
    assert stopped_instances[0]['instance_id'] == 'i-no-ebs-volume'
    assert stopped_instances[0]['ebs_monthly_cost'] == 0.0


@patch('boto3.resource')
@patch('boto3.client')
def test_scan_stopped_instances_multiple_instances(mock_boto_client, mock_boto_resource):
    """Test scanning multiple stopped instances."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    mock_volume1 = Mock()
    mock_volume1.size = 50
    mock_volume1.volume_type = 'gp2'
    
    mock_volume2 = Mock()
    mock_volume2.size = 100
    mock_volume2.volume_type = 'gp3'
    
    def mock_volume_side_effect(volume_id):
        if volume_id == 'vol-111':
            return mock_volume1
        elif volume_id == 'vol-222':
            return mock_volume2
        return Mock()
    
    mock_resource.Volume.side_effect = mock_volume_side_effect
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    launch_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    mock_paginator.paginate.return_value = [{
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-instance-1',
                        'InstanceType': 't2.micro',
                        'State': {'Name': 'stopped'},
                        'LaunchTime': launch_time,
                        'BlockDeviceMappings': [{
                            'Ebs': {'VolumeId': 'vol-111'}
                        }]
                    },
                    {
                        'InstanceId': 'i-instance-2',
                        'InstanceType': 't3.small',
                        'State': {'Name': 'stopped'},
                        'LaunchTime': launch_time,
                        'BlockDeviceMappings': [{
                            'Ebs': {'VolumeId': 'vol-222'}
                        }]
                    }
                ]
            }
        ]
    }]
    
    scanner = EC2Scanner()
    stopped_instances = scanner.scan_stopped_instances()
    
    assert len(stopped_instances) == 2
    instance_ids = [inst['instance_id'] for inst in stopped_instances]
    assert 'i-instance-1' in instance_ids
    assert 'i-instance-2' in instance_ids
    assert any(inst['ebs_monthly_cost'] == 5.0 for inst in stopped_instances) 
    assert any(inst['ebs_monthly_cost'] == 8.0 for inst in stopped_instances)  


@patch('boto3.resource')
@patch('boto3.client')
def test_calculate_ebs_cost_gp3_vs_gp2(mock_boto_client, mock_boto_resource):
    """Test EBS cost calculation for different volume types."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    mock_volume_gp3 = Mock()
    mock_volume_gp3.size = 100
    mock_volume_gp3.volume_type = 'gp3'
    
    mock_volume_gp2 = Mock()
    mock_volume_gp2.size = 100
    mock_volume_gp2.volume_type = 'gp2'
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    launch_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    mock_resource.Volume.return_value = mock_volume_gp3
    mock_paginator.paginate.return_value = [{
        'Reservations': [{
            'Instances': [{
                'InstanceId': 'i-gp3',
                'InstanceType': 't2.micro',
                'State': {'Name': 'stopped'},
                'LaunchTime': launch_time,
                'BlockDeviceMappings': [{
                    'Ebs': {'VolumeId': 'vol-gp3'}
                }]
            }]
        }]
    }]
    
    scanner = EC2Scanner()
    instances = scanner.scan_stopped_instances()
    assert instances[0]['ebs_monthly_cost'] == 8.0  
    
    mock_resource.Volume.return_value = mock_volume_gp2
    mock_paginator.paginate.return_value = [{
        'Reservations': [{
            'Instances': [{
                'InstanceId': 'i-gp2',
                'InstanceType': 't2.micro',
                'State': {'Name': 'stopped'},
                'LaunchTime': launch_time,
                'BlockDeviceMappings': [{
                    'Ebs': {'VolumeId': 'vol-gp2'}
                }]
            }]
        }]
    }]
    
    instances = scanner.scan_stopped_instances(use_cache=False)
    assert instances[0]['ebs_monthly_cost'] == 10.0  


@patch('boto3.resource')
@patch('boto3.client')
def test_calculate_ebs_cost_volume_access_error(mock_boto_client, mock_boto_resource):
    """Test EBS cost calculation when volume access fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    from botocore.exceptions import ClientError
    mock_resource.Volume.side_effect = ClientError(
        {'Error': {'Code': 'InvalidVolume.NotFound', 'Message': 'Volume not found'}},
        'describe_volume'
    )
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    launch_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    mock_paginator.paginate.return_value = [{
        'Reservations': [{
            'Instances': [{
                'InstanceId': 'i-missing-volume',
                'InstanceType': 't2.micro',
                'State': {'Name': 'stopped'},
                'LaunchTime': launch_time,
                'BlockDeviceMappings': [{
                    'Ebs': {'VolumeId': 'vol-missing'}
                }]
            }]
        }]
    }]
    
    scanner = EC2Scanner()
    instances = scanner.scan_stopped_instances()
    
    assert len(instances) == 1
    assert instances[0]['ebs_monthly_cost'] == 0.0


def test_generate_recommendation_monitor():
    """Test recommendation generation for recently stopped instances."""
    scanner = EC2Scanner()
    
    rec = scanner._generate_recommendation(3, 5.00)
    assert 'MONITOR' in rec
    assert '$5.00' in rec
    assert 'Recently stopped' in rec


def test_generate_recommendation_review():
    """Test recommendation generation for instances stopped 7-30 days."""
    scanner = EC2Scanner()
    
    rec = scanner._generate_recommendation(15, 10.00)
    assert 'REVIEW' in rec
    assert '$10.00' in rec
    assert '15 days' in rec


def test_generate_recommendation_terminate():
    """Test recommendation generation for instances stopped >30 days."""
    scanner = EC2Scanner()
    
    rec = scanner._generate_recommendation(45, 20.00)
    assert 'TERMINATE' in rec
    assert '$20.00' in rec
    assert '45 days' in rec


@patch('boto3.resource')
@patch('boto3.client')
def test_scan_stopped_instances_empty_result(mock_boto_client, mock_boto_resource):
    """Test scanning when no stopped instances exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{'Reservations': []}]
    
    scanner = EC2Scanner()
    stopped_instances = scanner.scan_stopped_instances()
    
    assert stopped_instances == []


@patch('boto3.resource')
@patch('boto3.client')
def test_calculate_ebs_cost_multiple_volumes(mock_boto_client, mock_boto_resource):
    """Test EBS cost calculation with multiple volumes per instance."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_resource = Mock()
    mock_boto_resource.return_value = mock_resource
    
    mock_volume1 = Mock()
    mock_volume1.size = 50
    mock_volume1.volume_type = 'gp2'
    
    mock_volume2 = Mock()
    mock_volume2.size = 30
    mock_volume2.volume_type = 'gp3'
    
    def mock_volume_side_effect(volume_id):
        if volume_id == 'vol-1':
            return mock_volume1
        elif volume_id == 'vol-2':
            return mock_volume2
        return Mock()
    
    mock_resource.Volume.side_effect = mock_volume_side_effect
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    launch_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    mock_paginator.paginate.return_value = [{
        'Reservations': [{
            'Instances': [{
                'InstanceId': 'i-multi-volume',
                'InstanceType': 't2.micro',
                'State': {'Name': 'stopped'},
                'LaunchTime': launch_time,
                'BlockDeviceMappings': [
                    {'Ebs': {'VolumeId': 'vol-1'}},
                    {'Ebs': {'VolumeId': 'vol-2'}}
                ]
            }]
        }]
    }]
    
    scanner = EC2Scanner()
    instances = scanner.scan_stopped_instances()
    
    assert instances[0]['ebs_monthly_cost'] == 7.4