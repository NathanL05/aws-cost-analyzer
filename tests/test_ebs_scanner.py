"""Tests for EBS scanner."""

from unittest.mock import patch, Mock
from datetime import datetime, timezone
from scanners.ebs_scanner import EBSScanner
import botocore.client


def test_ebs_scanner_initialization():
    """Test EBSScanner initialization."""
    scanner = EBSScanner()

    assert scanner.region == 'eu-west-1'

    assert isinstance(scanner.ec2_client, botocore.client.BaseClient)


@patch('boto3.client')
def test_scan_unattached_volumes_empty(mock_boto_client):
    """Test scanning when no volumes exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    # Mock paginator
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{'Volumes': []}]

    scanner = EBSScanner()
    volumes = scanner.scan_unattached_volumes()

    assert volumes == []


@patch('boto3.client')
def test_scan_unattached_volumes_with_attached_only(mock_boto_client):
    """Test scanning when only attached volumes exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{
        'Volumes': [{
            'VolumeId': 'vol-1234567890abcdef0',
            'Size': 10,
            'VolumeType': 'gp2',
            'AvailabilityZone': 'eu-west-1a',
            'CreateTime': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            'State': 'in-use',
            'Attachments': [{
                'InstanceId': 'i-1234567890abcdef0',
                'Device': '/dev/sda1',
                'State': 'attached'
            }]
        }]
    }]

    scanner = EBSScanner()
    volumes = scanner.scan_unattached_volumes()

    assert volumes == []


@patch('boto3.client')
def test_scan_unattached_volumes_with_unattached(mock_boto_client):
    """Test scanning with unattached volumes."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator

    create_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    mock_paginator.paginate.return_value = [{
        'Volumes': [{
            'VolumeId': 'vol-1234567890abcdef0',
            'Size': 10,
            'VolumeType': 'gp3',
            'AvailabilityZone': 'eu-west-1a',
            'CreateTime': create_time,
            'State': 'available',
            'Attachments': []
        }]
    }]

    scanner = EBSScanner()
    volumes = scanner.scan_unattached_volumes()

    assert len(volumes) == 1
    volume = volumes[0]
    assert volume['volume_id'] == 'vol-1234567890abcdef0'
    assert volume['size'] == 10
    assert volume['volume_type'] == 'gp3'
    assert volume['availability_zone'] == 'eu-west-1a'
    assert 'age_days' in volume
    assert 'monthly_cost' in volume
    assert 'recommendation' in volume


@patch('boto3.client')
def test_scan_unattached_volumes_mixed(mock_boto_client):
    """Test scanning with both attached and unattached volumes."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator

    create_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    mock_paginator.paginate.return_value = [{
        'Volumes': [
            {
                'VolumeId': 'vol-1234567890abcdef0',
                'Size': 10,
                'VolumeType': 'gp2',
                'AvailabilityZone': 'eu-west-1a',
                'CreateTime': create_time,
                'State': 'in-use',
                'Attachments': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'Device': '/dev/sda1',
                    'State': 'attached'
                }]
            },
            {
                'VolumeId': 'vol-0987654321fedcba0',
                'Size': 20,
                'VolumeType': 'gp2',
                'AvailabilityZone': 'eu-west-1a',
                'CreateTime': create_time,
                'State': 'available',
                'Attachments': []
            }
        ]
    }]

    scanner = EBSScanner()
    volumes = scanner.scan_unattached_volumes()

    assert len(volumes) == 1
    assert volumes[0]['volume_id'] == 'vol-0987654321fedcba0'
    assert volumes[0]['volume_type'] == 'gp2'


def test_calculate_monthly_cost():
    """Test monthly cost calculation for different volume types."""
    scanner = EBSScanner()

    assert scanner._calculate_monthly_cost(10, "gp3") == 0.80
    assert scanner._calculate_monthly_cost(10, "gp2") == 1.00
    assert scanner._calculate_monthly_cost(10, "io1") == 1.25
    assert scanner._calculate_monthly_cost(10, "st1") == 0.45
    assert scanner._calculate_monthly_cost(10, "sc1") == 0.15
    assert scanner._calculate_monthly_cost(10, "standard") == 0.50
    assert scanner._calculate_monthly_cost(10, "unknown") == 1.00


def test_generate_recommendation():
    """Test recommendation generation based on age and cost."""
    scanner = EBSScanner()

    recommendation = scanner._generate_recommendation(3, 1.50)
    assert "MONITOR" in recommendation
    assert "$1.50" in recommendation

    recommendation = scanner._generate_recommendation(14, 2.00)
    assert "REVIEW" in recommendation
    assert "$2.00" in recommendation

    recommendation = scanner._generate_recommendation(45, 3.00)
    assert "DELETE" in recommendation
    assert "$3.00" in recommendation


def test_process_unattached_volume():
    """Test processing of individual volume data."""
    scanner = EBSScanner()

    create_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    volume_data = {
        'VolumeId': 'vol-12345',
        'Size': 50,
        'VolumeType': 'gp3',
        'AvailabilityZone': 'eu-west-1a',
        'CreateTime': create_time,
        'State': 'available'
    }

    processed = scanner._process_unattached_volume(volume_data)

    assert processed['volume_id'] == 'vol-12345'
    assert processed['size'] == 50
    assert processed['volume_type'] == 'gp3'
    assert processed['availability_zone'] == 'eu-west-1a'
    assert processed['create_time'] == create_time
    assert 'age_days' in processed
    assert processed['age_days'] >= 0
    assert processed['monthly_cost'] == 4.00 
    assert any(keyword in processed['recommendation'] for keyword in ['MONITOR', 'REVIEW', 'DELETE'])


@patch('boto3.client')
def test_scan_unattached_volumes_error_handling(mock_boto_client):
    """Test error handling when AWS API fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    from botocore.exceptions import ClientError
    mock_paginator.paginate.side_effect = ClientError(
        {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'You are not authorized'}},
        'describe_volumes'
    )

    scanner = EBSScanner()
    volumes = scanner.scan_unattached_volumes()

    assert isinstance(volumes, list)
    assert volumes == []


def test_volume_cost_calculation_edge_cases():
    """Test cost calculation with edge cases."""
    scanner = EBSScanner()

    assert scanner._calculate_monthly_cost(0, "gp3") == 0.00

    cost = scanner._calculate_monthly_cost(10000, "gp3")
    assert cost == 800.00  

    assert scanner._calculate_monthly_cost(10, None) == 1.00  
