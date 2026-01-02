"""Tests for S3 scanner."""

from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta
from scanners.s3_scanner import S3Scanner
import botocore.client


def test_s3_scanner_initialization():
    """Test S3Scanner initialization."""
    scanner = S3Scanner()
    
    assert isinstance(scanner.s3_client, botocore.client.BaseClient)


@patch('boto3.client')
def test_scan_unused_buckets_empty(mock_boto_client):
    """Test scanning when no buckets exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_client.list_buckets.return_value = {'Buckets': []}
    
    scanner = S3Scanner()
    result = scanner.scan_unused_buckets()
    
    assert result == []


@patch('boto3.client')
def test_scan_unused_buckets_with_empty_bucket(mock_boto_client):
    """Test scanning with empty bucket."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    creation_date = datetime.now(timezone.utc) - timedelta(days=60)
    mock_client.list_buckets.return_value = {
        'Buckets': [{
            'Name': 'test-empty-bucket',
            'CreationDate': creation_date
        }]
    }
    
    mock_client.list_objects_v2.return_value = {}
    
    scanner = S3Scanner()
    result = scanner.scan_unused_buckets()
    
    assert len(result) == 1
    assert result[0]['bucket_name'] == 'test-empty-bucket'
    assert result[0]['is_empty'] is True
    assert result[0]['age_days'] >= 60


@patch('boto3.client')
def test_scan_unused_buckets_with_old_bucket(mock_boto_client):
    """Test scanning with old bucket (>180 days should get REVIEW recommendation)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    creation_date = datetime.now(timezone.utc) - timedelta(days=200)
    mock_client.list_buckets.return_value = {
        'Buckets': [{
            'Name': 'test-old-bucket',
            'CreationDate': creation_date
        }]
    }
    
    mock_client.list_objects_v2.return_value = {
        'Contents': [{'Key': 'file1.txt'}]
    }
    
    scanner = S3Scanner()
    result = scanner.scan_unused_buckets()
    
    assert len(result) == 1
    assert result[0]['bucket_name'] == 'test-old-bucket'
    assert result[0]['is_empty'] is False
    assert result[0]['age_days'] >= 200
    assert 'REVIEW' in result[0]['recommendation']


@patch('boto3.client')
def test_scan_unused_buckets_with_recent_bucket(mock_boto_client):
    """Test scanning with recent bucket (should not be flagged)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    creation_date = datetime.now(timezone.utc) - timedelta(days=30)
    mock_client.list_buckets.return_value = {
        'Buckets': [{
            'Name': 'test-recent-bucket',
            'CreationDate': creation_date
        }]
    }
    
    mock_client.list_objects_v2.return_value = {
        'Contents': [{'Key': 'file1.txt'}]
    }
    
    scanner = S3Scanner()
    result = scanner.scan_unused_buckets()
    
    assert len(result) == 0


@patch('boto3.client')
def test_scan_unused_buckets_access_denied(mock_boto_client):
    """Test scanning when bucket access is denied."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    creation_date = datetime.now(timezone.utc) - timedelta(days=60)
    mock_client.list_buckets.return_value = {
        'Buckets': [{
            'Name': 'test-private-bucket',
            'CreationDate': creation_date
        }]
    }
    
    from botocore.exceptions import ClientError
    mock_client.list_objects_v2.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
        'list_objects_v2'
    )
    
    scanner = S3Scanner()
    result = scanner.scan_unused_buckets()
    
    assert len(result) == 0


@patch('boto3.client')
def test_scan_unused_buckets_error_handling(mock_boto_client):
    """Test error handling when AWS API fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    from botocore.exceptions import ClientError
    mock_client.list_buckets.side_effect = ClientError(
        {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'You are not authorized'}},
        'list_buckets'
    )
    
    scanner = S3Scanner()
    result = scanner.scan_unused_buckets()
    
    assert isinstance(result, list)
    assert result == []


def test_generate_recommendation_delete():
    """Test recommendation generation for deletion."""
    scanner = S3Scanner()
    
    rec = scanner._generate_recommendation(is_empty=True, age_days=60)
    assert 'DELETE' in rec
    assert 'Empty bucket' in rec


def test_generate_recommendation_review():
    """Test recommendation generation for review."""
    scanner = S3Scanner()
    
    rec = scanner._generate_recommendation(is_empty=False, age_days=200)
    assert 'REVIEW' in rec
    assert 'days old' in rec


def test_generate_recommendation_monitor():
    """Test recommendation generation for monitoring."""
    scanner = S3Scanner()
    
    rec = scanner._generate_recommendation(is_empty=False, age_days=50)
    assert 'MONITOR' in rec
    assert 'Recently created' in rec or 'has content' in rec
