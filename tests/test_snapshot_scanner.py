"""Tests for Snapshot scanner."""

from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta
from scanners.snapshot_scanner import SnapshotScanner
import botocore.client


def test_snapshot_scanner_initialization():
    """Test SnapshotScanner initialization."""
    scanner = SnapshotScanner()

    assert scanner.region == 'eu-west-1'
    assert isinstance(scanner.ec2_client, botocore.client.BaseClient)


@patch('boto3.client')
def test_scan_old_snapshots_empty(mock_boto_client):
    """Test scanning when no snapshots exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{'Snapshots': []}]

    scanner = SnapshotScanner()
    snapshots = scanner.scan_old_snapshots()

    assert snapshots == []


@patch('boto3.client')
def test_scan_old_snapshots_with_new_only(mock_boto_client):
    """Test scanning when only new snapshots exist (should return empty)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator

    recent_time = datetime.now(timezone.utc)
    mock_paginator.paginate.return_value = [{
        'Snapshots': [{
            'SnapshotId': 'snap-1234567890abcdef0',
            'VolumeId': 'vol-1234567890abcdef0',
            'VolumeSize': 10,
            'StartTime': recent_time,
            'State': 'completed'
        }]
    }]

    mock_client.describe_volumes.return_value = {
        'Volumes': [{
            'VolumeId': 'vol-1234567890abcdef0',
            'State': 'available'
        }]
    }

    scanner = SnapshotScanner()
    snapshots = scanner.scan_old_snapshots()

    assert snapshots == []


@patch('boto3.client')
def test_scan_old_snapshots_with_old(mock_boto_client):
    """Test scanning with old snapshots."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator

    old_time = datetime.now(timezone.utc) - timedelta(days=120)
    mock_paginator.paginate.return_value = [{
        'Snapshots': [{
            'SnapshotId': 'snap-1234567890abcdef0',
            'VolumeId': 'vol-1234567890abcdef0',
            'VolumeSize': 10,
            'StartTime': old_time,
            'State': 'completed'
        }]
    }]

    mock_client.describe_volumes.return_value = {
        'Volumes': [{
            'VolumeId': 'vol-1234567890abcdef0',
            'State': 'available'
        }]
    }

    scanner = SnapshotScanner()
    snapshots = scanner.scan_old_snapshots()

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot['snapshot_id'] == 'snap-1234567890abcdef0'
    assert snapshot['volume_id'] == 'vol-1234567890abcdef0'
    assert snapshot['start_time'] == old_time
    assert snapshot['age_days'] >= 120  
    assert snapshot['monthly_cost'] == 0.5  
    assert snapshot['volume_exists'] is True
    assert 'MONITOR' in snapshot['recommendation']


@patch('boto3.client')
def test_scan_old_snapshots_orphaned(mock_boto_client):
    """Test scanning with orphaned snapshots (volume doesn't exist)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator

    very_old_time = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    mock_paginator.paginate.return_value = [{
        'Snapshots': [{
            'SnapshotId': 'snap-0987654321fedcba0',
            'VolumeId': 'vol-deleted123456789',
            'VolumeSize': 20,
            'StartTime': very_old_time,
            'State': 'completed'
        }]
    }]

    from botocore.exceptions import ClientError
    mock_client.describe_volumes.side_effect = ClientError(
        {'Error': {'Code': 'InvalidVolume.NotFound'}},
        'describe_volumes'
    )

    scanner = SnapshotScanner()
    snapshots = scanner.scan_old_snapshots()

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot['snapshot_id'] == 'snap-0987654321fedcba0'
    assert snapshot['volume_exists'] is False
    assert snapshot['monthly_cost'] == 1.0  
    assert 'DELETE' in snapshot['recommendation']
    assert 'Orphaned snapshot' in snapshot['recommendation']


@patch('boto3.client')
def test_scan_old_snapshots_mixed(mock_boto_client):
    """Test scanning with both old and new snapshots."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator

    recent_time = datetime.now(timezone.utc)
    old_time = datetime.now(timezone.utc) - timedelta(days=120)

    mock_paginator.paginate.return_value = [{
        'Snapshots': [
            {
                'SnapshotId': 'snap-new123456789',
                'VolumeId': 'vol-new123456789',
                'VolumeSize': 10,
                'StartTime': recent_time,  
                'State': 'completed'
            },
            {
                'SnapshotId': 'snap-old123456789',
                'VolumeId': 'vol-old123456789',
                'VolumeSize': 15,
                'StartTime': old_time,  
                'State': 'completed'
            }
        ]
    }]

    def mock_describe_volumes(**kwargs):
        volume_ids = kwargs.get('VolumeIds', [])
        if volume_ids == ['vol-new123456789']:
            return {'Volumes': [{'VolumeId': 'vol-new123456789'}]}
        elif volume_ids == ['vol-old123456789']:
            return {'Volumes': [{'VolumeId': 'vol-old123456789'}]}
        return {'Volumes': []}

    mock_client.describe_volumes.side_effect = mock_describe_volumes

    scanner = SnapshotScanner()
    snapshots = scanner.scan_old_snapshots()

    assert len(snapshots) == 1
    assert snapshots[0]['snapshot_id'] == 'snap-old123456789'


def test_process_snapshots_new():
    """Test processing a new snapshot (should return None)."""
    scanner = SnapshotScanner()

    recent_time = datetime.now(timezone.utc)
    snapshot = {
        'SnapshotId': 'snap-12345',
        'VolumeId': 'vol-12345',
        'VolumeSize': 10,
        'StartTime': recent_time,
        'State': 'completed'
    }

    result = scanner._process_snapshots(snapshot, 90)
    assert result is None


def test_process_snapshots_old():
    """Test processing an old snapshot."""
    scanner = SnapshotScanner()

    old_time = datetime(2024, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    snapshot = {
        'SnapshotId': 'snap-12345',
        'VolumeId': 'vol-12345',
        'VolumeSize': 25,
        'StartTime': old_time,
        'State': 'completed'
    }

    with patch.object(scanner, '_check_volume_exists', return_value=True):
        result = scanner._process_snapshots(snapshot, 90)

    assert result is not None
    assert result['snapshot_id'] == 'snap-12345'
    assert result['volume_id'] == 'vol-12345'
    assert result['monthly_cost'] == 1.25  
    assert result['volume_exists'] is True


@patch('boto3.client')
def test_check_volume_exists_true(mock_boto_client):
    """Test volume existence check when volume exists."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    mock_client.describe_volumes.return_value = {
        'Volumes': [{'VolumeId': 'vol-12345'}]
    }

    scanner = SnapshotScanner()
    exists = scanner._check_volume_exists('vol-12345')

    assert exists is True
    mock_client.describe_volumes.assert_called_once_with(VolumeIds=['vol-12345'])


@patch('boto3.client')
def test_check_volume_exists_false(mock_boto_client):
    """Test volume existence check when volume doesn't exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    from botocore.exceptions import ClientError
    mock_client.describe_volumes.side_effect = ClientError(
        {'Error': {'Code': 'InvalidVolume.NotFound'}},
        'describe_volumes'
    )

    scanner = SnapshotScanner()
    exists = scanner._check_volume_exists('vol-missing')

    assert exists is False


@patch('boto3.client')
def test_check_volume_exists_unknown(mock_boto_client):
    """Test volume existence check with unknown volume."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    scanner = SnapshotScanner()
    exists = scanner._check_volume_exists('unknown')

    assert exists is False
    mock_client.describe_volumes.assert_not_called()


@patch('boto3.client')
def test_check_volume_exists_other_error(mock_boto_client):
    """Test volume existence check with other AWS errors."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    from botocore.exceptions import ClientError
    mock_client.describe_volumes.side_effect = ClientError(
        {'Error': {'Code': 'UnauthorizedOperation'}},
        'describe_volumes'
    )

    scanner = SnapshotScanner()

    try:
        scanner._check_volume_exists('vol-12345')
        assert False, "Should have raised ClientError"
    except ClientError as e:
        assert e.response['Error']['Code'] == 'UnauthorizedOperation'


def test_generate_recommendation_monitor():
    """Test recommendation generation for monitoring."""
    scanner = SnapshotScanner()

    rec = scanner._generate_recommendation(100, 2.50, True)
    assert 'MONITOR' in rec
    assert '$2.50' in rec
    assert '100 days' in rec


def test_generate_recommendation_review():
    """Test recommendation generation for review."""
    scanner = SnapshotScanner()

    rec = scanner._generate_recommendation(200, 3.75, True)
    assert 'REVIEW' in rec
    assert '$3.75' in rec
    assert '200 days' in rec


def test_generate_recommendation_delete():
    """Test recommendation generation for deletion."""
    scanner = SnapshotScanner()

    rec = scanner._generate_recommendation(200, 1.00, False)
    assert 'DELETE' in rec
    assert '$1.00' in rec
    assert 'Orphaned snapshot' in rec


@patch('boto3.client')
def test_scan_old_snapshots_error_handling(mock_boto_client):
    """Test error handling when AWS API fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    from botocore.exceptions import ClientError
    mock_paginator.paginate.side_effect = ClientError(
        {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'You are not authorized'}},
        'describe_snapshots'
    )

    scanner = SnapshotScanner()
    snapshots = scanner.scan_old_snapshots()

    assert isinstance(snapshots, list)
    assert snapshots == []


def test_process_snapshots_edge_cases():
    """Test processing snapshots with edge cases."""
    scanner = SnapshotScanner()

    old_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    snapshot = {
        'SnapshotId': 'snap-zero',
        'VolumeId': 'vol-zero',
        'VolumeSize': 0,
        'StartTime': old_time,
        'State': 'completed'
    }

    with patch.object(scanner, '_check_volume_exists', return_value=True):
        result = scanner._process_snapshots(snapshot, 90)

    assert result['monthly_cost'] == 0.0

    snapshot_large = {
        'SnapshotId': 'snap-large',
        'VolumeId': 'vol-large',
        'VolumeSize': 10000,
        'StartTime': old_time,
        'State': 'completed'
    }

    with patch.object(scanner, '_check_volume_exists', return_value=True):
        result_large = scanner._process_snapshots(snapshot_large, 90)

    assert result_large['monthly_cost'] == 500.0  
