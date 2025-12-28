from scanners.eip_scanner import EIPScanner
from unittest.mock import patch, Mock
import botocore.client

def test_eip_scanner_initialization():
    """Test EIPScanner initialization."""
    scanner = EIPScanner()
    
    assert scanner.region == 'eu-west-1'
    assert isinstance(scanner.ec2_client, botocore.client.BaseClient)

@patch('boto3.client')
def test_scan_unassociated_eips_empty(mock_boto_client):
    """Test scanning when no unassociated EIPs exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client 

    mock_client.describe_addresses.return_value = {'Addresses': []}

    scanner = EIPScanner()
    result = scanner.scan_unassociated_eips()
    assert result == []

@patch('boto3.client')
def test_scan_unassociated_eips_with_unassociated_eips(mock_boto_client):
    """Test scanning when unassociated EIPs exist."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client 

    mock_client.describe_addresses.return_value = {'Addresses': [{'AllocationId': 'eipalloc-0123456789abcdef0', 'PublicIp': '192.0.2.1', 'AssociationId': None}]}

    scanner = EIPScanner()
    result = scanner.scan_unassociated_eips()
    assert result == [{'allocation_id': 'eipalloc-0123456789abcdef0', 'public_ip': '192.0.2.1', 'monthly_cost': 3.6, 'recommendation': 'RELEASE - Unassociated EIP wasting $3.60/month'}]

@patch('boto3.client')
def test_scan_unassociated_eips_with_associated_only(mock_boto_client):
    """Test scanning when only associated EIPs exist (should return empty)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client 

    mock_client.describe_addresses.return_value = {'Addresses': [{'AllocationId': 'eipalloc-0123456789abcdef0', 'PublicIp': '192.0.2.1', 'AssociationId': 'eipassoc-0123456789abcdef0'}]}

    scanner = EIPScanner()
    result = scanner.scan_unassociated_eips()
    assert result == []

@patch('boto3.client')
def test_scan_unassociated_eips_missing_association_id_key(mock_boto_client):
    """Test scanning when AssociationId key doesn't exist (should be included)."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client 

    mock_client.describe_addresses.return_value = {'Addresses': [{'AllocationId': 'eipalloc-0987654321fedcba0', 'PublicIp': '192.0.2.2'}]}

    scanner = EIPScanner()
    result = scanner.scan_unassociated_eips()
    assert len(result) == 1
    assert result[0]['allocation_id'] == 'eipalloc-0987654321fedcba0'
    assert result[0]['public_ip'] == '192.0.2.2'
    assert result[0]['monthly_cost'] == 3.6

@patch('boto3.client')
def test_scan_unassociated_eips_error_handling(mock_boto_client):
    """Test error handling when AWS API fails."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    
    from botocore.exceptions import ClientError
    mock_client.describe_addresses.side_effect = ClientError(
        {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'You are not authorized'}},
        'describe_addresses'
    )

    scanner = EIPScanner()
    result = scanner.scan_unassociated_eips()
    assert isinstance(result, list)
    assert result == []