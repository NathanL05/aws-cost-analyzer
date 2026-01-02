"""Tests for Multi-region scanner."""

from unittest.mock import patch, Mock
from scanners.multi_region_scanner import MultiRegionScanner


@patch('scanners.multi_region_scanner.EC2Scanner')
@patch('scanners.multi_region_scanner.EBSScanner')
@patch('scanners.multi_region_scanner.SnapshotScanner')
@patch('scanners.multi_region_scanner.EIPScanner')
def test_scan_all_regions(mock_eip, mock_snapshot, mock_ebs, mock_ec2):
    """Test scanning all regions."""
    mock_ec2_instance = Mock()
    mock_ec2_instance.scan_stopped_instances.return_value = [
        {'instance_id': 'i-123', 'ebs_monthly_cost': 10.0}
    ]
    mock_ec2.return_value = mock_ec2_instance
    
    mock_ebs_instance = Mock()
    mock_ebs_instance.scan_unattached_volumes.return_value = [
        {'volume_id': 'vol-123', 'monthly_cost': 5.0}
    ]
    mock_ebs.return_value = mock_ebs_instance
    
    mock_snapshot_instance = Mock()
    mock_snapshot_instance.scan_old_snapshots.return_value = [
        {'snapshot_id': 'snap-123', 'monthly_cost': 2.0}
    ]
    mock_snapshot.return_value = mock_snapshot_instance
    
    mock_eip_instance = Mock()
    mock_eip_instance.scan_unassociated_eips.return_value = [
        {'allocation_id': 'eip-123', 'monthly_cost': 3.6}
    ]
    mock_eip.return_value = mock_eip_instance
    
    scanner = MultiRegionScanner()
    results = scanner.scan_all_regions(max_workers=2)
    
    assert len(results) == len(MultiRegionScanner.REGIONS)
    
    first_region = list(results.values())[0]
    assert 'stopped_instances' in first_region
    assert 'unattached_volumes' in first_region
    assert 'old_snapshots' in first_region
    assert 'unassociated_eips' in first_region


@patch('scanners.multi_region_scanner.EC2Scanner')
@patch('scanners.multi_region_scanner.EBSScanner')
@patch('scanners.multi_region_scanner.SnapshotScanner')
@patch('scanners.multi_region_scanner.EIPScanner')
def test_scan_all_regions_with_error(mock_eip, mock_snapshot, mock_ebs, mock_ec2):
    """Test scanning when one region fails."""
    mock_ec2_instance = Mock()
    mock_ec2_instance.scan_stopped_instances.return_value = []
    mock_ec2.return_value = mock_ec2_instance
    
    mock_ebs_instance = Mock()
    mock_ebs_instance.scan_unattached_volumes.return_value = []
    mock_ebs.return_value = mock_ebs_instance
    
    mock_snapshot_instance = Mock()
    mock_snapshot_instance.scan_old_snapshots.return_value = []
    mock_snapshot.return_value = mock_snapshot_instance
    
    mock_eip_instance = Mock()
    mock_eip_instance.scan_unassociated_eips.side_effect = Exception("AWS Error")
    mock_eip.return_value = mock_eip_instance
    
    scanner = MultiRegionScanner()
    
    results = scanner.scan_all_regions(max_workers=2)
    
    assert len(results) == len(MultiRegionScanner.REGIONS)


def test_scan_region_structure():
    """Test that _scan_region returns correct structure."""
    scanner = MultiRegionScanner()
    
    with patch('scanners.multi_region_scanner.EC2Scanner') as mock_ec2, \
         patch('scanners.multi_region_scanner.EBSScanner') as mock_ebs, \
         patch('scanners.multi_region_scanner.SnapshotScanner') as mock_snapshot, \
         patch('scanners.multi_region_scanner.EIPScanner') as mock_eip:
        
        mock_ec2_instance = Mock()
        mock_ec2_instance.scan_stopped_instances.return_value = []
        mock_ec2.return_value = mock_ec2_instance
        
        mock_ebs_instance = Mock()
        mock_ebs_instance.scan_unattached_volumes.return_value = []
        mock_ebs.return_value = mock_ebs_instance
        
        mock_snapshot_instance = Mock()
        mock_snapshot_instance.scan_old_snapshots.return_value = []
        mock_snapshot.return_value = mock_snapshot_instance
        
        mock_eip_instance = Mock()
        mock_eip_instance.scan_unassociated_eips.return_value = []
        mock_eip.return_value = mock_eip_instance
        
        result = scanner._scan_region('eu-west-1')
        
        assert 'stopped_instances' in result
        assert 'unattached_volumes' in result
        assert 'old_snapshots' in result
        assert 'unassociated_eips' in result
        assert isinstance(result['stopped_instances'], list)
        assert isinstance(result['unattached_volumes'], list)
        assert isinstance(result['old_snapshots'], list)
        assert isinstance(result['unassociated_eips'], list)
