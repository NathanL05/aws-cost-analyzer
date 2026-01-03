"""Tests for IAM scanner."""

from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta
from scanners.iam_scanner import IAMScanner
import botocore.client


def test_iam_scanner_initialization():
    """Test IAMScanner initialization."""
    scanner = IAMScanner()
    
    assert isinstance(scanner.iam_client, botocore.client.BaseClient)


@patch('boto3.client')
def test_scan_unused_access_keys_no_users(mock_boto_client):
    """Test scanning when no users exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{'Users': []}]
    
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys()
    
    assert result == []


@patch('boto3.client')
def test_scan_unused_access_keys_unused_key(mock_boto_client):
    """Test scanning with unused access key (>90 days)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    create_date = datetime.now(timezone.utc) - timedelta(days=120)
    last_used_date = datetime.now(timezone.utc) - timedelta(days=100)
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'test-user'
        }]
    }]
    
    mock_client.list_access_keys.return_value = {
        'AccessKeyMetadata': [{
            'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
            'CreateDate': create_date
        }]
    }
    
    mock_client.get_access_key_last_used.return_value = {
        'AccessKeyLastUsed': {
            'LastUsedDate': last_used_date
        }
    }
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys(days_threshold=90)
    
    assert len(result) == 1
    assert result[0]['username'] == 'test-user'
    assert result[0]['access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
    assert result[0]['days_unused'] >= 90
    assert 'DELETE' in result[0]['recommendation']


@patch('boto3.client')
def test_scan_unused_access_keys_never_used(mock_boto_client):
    """Test scanning with access key that was never used."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    create_date = datetime.now(timezone.utc) - timedelta(days=120)
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'test-user-never-used'
        }]
    }]
    
    mock_client.list_access_keys.return_value = {
        'AccessKeyMetadata': [{
            'AccessKeyId': 'AKIANEVERUSEDEXAMPLE',
            'CreateDate': create_date
        }]
    }
    
    mock_client.get_access_key_last_used.return_value = {
        'AccessKeyLastUsed': {}
    }
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys(days_threshold=90)
    
    assert len(result) == 1
    assert result[0]['username'] == 'test-user-never-used'
    assert result[0]['last_used'] == 'Never'
    assert result[0]['days_unused'] >= 90


@patch('boto3.client')
def test_scan_unused_access_keys_recently_used(mock_boto_client):
    """Test scanning with recently used access key (should not be flagged)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    create_date = datetime.now(timezone.utc) - timedelta(days=200)
    last_used_date = datetime.now(timezone.utc) - timedelta(days=30)
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'active-user'
        }]
    }]
    
    mock_client.list_access_keys.return_value = {
        'AccessKeyMetadata': [{
            'AccessKeyId': 'AKIARECENTLYUSED',
            'CreateDate': create_date
        }]
    }
    
    mock_client.get_access_key_last_used.return_value = {
        'AccessKeyLastUsed': {
            'LastUsedDate': last_used_date
        }
    }
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys(days_threshold=90)
    
    assert len(result) == 0


@patch('boto3.client')
def test_scan_unused_access_keys_custom_threshold(mock_boto_client):
    """Test scanning with custom days threshold."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    create_date = datetime.now(timezone.utc) - timedelta(days=60)
    last_used_date = datetime.now(timezone.utc) - timedelta(days=45)
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'test-user-custom'
        }]
    }]
    
    mock_client.list_access_keys.return_value = {
        'AccessKeyMetadata': [{
            'AccessKeyId': 'AKIACUSTOMTHRESHOLD',
            'CreateDate': create_date
        }]
    }
    
    mock_client.get_access_key_last_used.return_value = {
        'AccessKeyLastUsed': {
            'LastUsedDate': last_used_date
        }
    }
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys(days_threshold=30)
    
    assert len(result) == 1
    assert result[0]['days_unused'] >= 30
    
    result = scanner.scan_unused_access_keys(days_threshold=60)
    assert len(result) == 0


@patch('boto3.client')
def test_scan_unused_access_keys_user_without_keys(mock_boto_client):
    """Test scanning user with no access keys."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'user-no-keys'
        }]
    }]
    
    mock_client.list_access_keys.return_value = {
        'AccessKeyMetadata': []
    }
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys()
    
    assert result == []


@patch('boto3.client')
def test_scan_unused_access_keys_multiple_users(mock_boto_client):
    """Test scanning multiple users with mixed results."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    create_date_old = datetime.now(timezone.utc) - timedelta(days=120)
    last_used_old = datetime.now(timezone.utc) - timedelta(days=100)
    
    create_date_recent = datetime.now(timezone.utc) - timedelta(days=200)
    last_used_recent = datetime.now(timezone.utc) - timedelta(days=30)
    
    mock_paginator.paginate.return_value = [{
        'Users': [
            {'UserName': 'user-with-unused-key'},
            {'UserName': 'user-with-active-key'}
        ]
    }]
    
    def list_access_keys_side_effect(UserName):
        if UserName == 'user-with-unused-key':
            return {
                'AccessKeyMetadata': [{
                    'AccessKeyId': 'AKIAUNUSEDKEY',
                    'CreateDate': create_date_old
                }]
            }
        elif UserName == 'user-with-active-key':
            return {
                'AccessKeyMetadata': [{
                    'AccessKeyId': 'AKIAACTIVEKEY',
                    'CreateDate': create_date_recent
                }]
            }
        return {'AccessKeyMetadata': []}
    
    def get_access_key_last_used_side_effect(AccessKeyId):
        if AccessKeyId == 'AKIAUNUSEDKEY':
            return {
                'AccessKeyLastUsed': {
                    'LastUsedDate': last_used_old
                }
            }
        elif AccessKeyId == 'AKIAACTIVEKEY':
            return {
                'AccessKeyLastUsed': {
                    'LastUsedDate': last_used_recent
                }
            }
        return {'AccessKeyLastUsed': {}}
    
    mock_client.list_access_keys.side_effect = list_access_keys_side_effect
    mock_client.get_access_key_last_used.side_effect = get_access_key_last_used_side_effect
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys(days_threshold=90)
    
    assert len(result) == 1
    assert result[0]['username'] == 'user-with-unused-key'
    assert result[0]['access_key_id'] == 'AKIAUNUSEDKEY'


@patch('boto3.client')
def test_scan_unused_access_keys_list_keys_error(mock_boto_client):
    """Test error handling when list_access_keys fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'user-with-error'
        }]
    }]
    
    from botocore.exceptions import ClientError
    mock_client.list_access_keys.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
        'list_access_keys'
    )
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys()
    
    assert result == []


@patch('boto3.client')
def test_scan_unused_access_keys_get_last_used_error(mock_boto_client):
    """Test error handling when get_access_key_last_used fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    create_date = datetime.now(timezone.utc) - timedelta(days=120)
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'user-with-last-used-error'
        }]
    }]
    
    mock_client.list_access_keys.return_value = {
        'AccessKeyMetadata': [{
            'AccessKeyId': 'AKIAERRORKEY',
            'CreateDate': create_date
        }]
    }
    
    from botocore.exceptions import ClientError
    mock_client.get_access_key_last_used.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
        'get_access_key_last_used'
    )
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys()
    
    # Should skip the key and return empty list
    assert result == []


@patch('boto3.client')
def test_scan_unused_access_keys_api_error(mock_boto_client):
    """Test error handling when list_users API fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    from botocore.exceptions import ClientError
    mock_paginator.paginate.side_effect = ClientError(
        {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'You are not authorized'}},
        'list_users'
    )
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys()
    
    assert isinstance(result, list)
    assert result == []


@patch('boto3.client')
def test_scan_unused_access_keys_multiple_keys_per_user(mock_boto_client):
    """Test scanning user with multiple access keys."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    mock_paginator = Mock()
    mock_client.get_paginator.return_value = mock_paginator
    
    create_date_unused = datetime.now(timezone.utc) - timedelta(days=120)
    last_used_unused = datetime.now(timezone.utc) - timedelta(days=100)
    
    create_date_active = datetime.now(timezone.utc) - timedelta(days=200)
    last_used_active = datetime.now(timezone.utc) - timedelta(days=30)
    
    mock_paginator.paginate.return_value = [{
        'Users': [{
            'UserName': 'user-multiple-keys'
        }]
    }]
    
    mock_client.list_access_keys.return_value = {
        'AccessKeyMetadata': [
            {
                'AccessKeyId': 'AKIAUNUSEDKEY1',
                'CreateDate': create_date_unused
            },
            {
                'AccessKeyId': 'AKIAACTIVEKEY1',
                'CreateDate': create_date_active
            }
        ]
    }
    
    def get_access_key_last_used_side_effect(AccessKeyId):
        if AccessKeyId == 'AKIAUNUSEDKEY1':
            return {
                'AccessKeyLastUsed': {
                    'LastUsedDate': last_used_unused
                }
            }
        elif AccessKeyId == 'AKIAACTIVEKEY1':
            return {
                'AccessKeyLastUsed': {
                    'LastUsedDate': last_used_active
                }
            }
        return {'AccessKeyLastUsed': {}}
    
    mock_client.get_access_key_last_used.side_effect = get_access_key_last_used_side_effect
    
    scanner = IAMScanner()
    result = scanner.scan_unused_access_keys(days_threshold=90)
    
    assert len(result) == 1
    assert result[0]['access_key_id'] == 'AKIAUNUSEDKEY1'