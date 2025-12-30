"""Tests for cost analyzer."""

from unittest.mock import patch, Mock
from analyzers.cost_analyzer import CostAnalyzer


@patch('analyzers.cost_analyzer.CostExplorerAnalyzer')
def test_calculate_total_waste_empty(mock_cost_explorer_class):
    """Test with no scan results."""
    mock_explorer = Mock()
    mock_explorer.get_ec2_actual_cost.return_value = 0.0
    mock_explorer.get_ebs_actual_cost.return_value = 0.0
    mock_explorer.get_total_monthly_cost.return_value = 0.0
    mock_cost_explorer_class.return_value = mock_explorer
    
    analyzer = CostAnalyzer()
    results = analyzer.calculate_total_waste({})

    assert results['estimated_waste']['total'] == 0.0
    assert results['resource_counts']['stopped_instances'] == 0
    assert results['actual_costs']['total_monthly'] == 0.0

@patch('analyzers.cost_analyzer.CostExplorerAnalyzer')
def test_calculate_total_waste_with_results(mock_cost_explorer_class):
    """Test with actual scan results."""
    mock_explorer = Mock()
    mock_explorer.get_ec2_actual_cost.return_value = 100.0
    mock_explorer.get_ebs_actual_cost.return_value = 50.0
    mock_explorer.get_total_monthly_cost.return_value = 200.0
    mock_cost_explorer_class.return_value = mock_explorer
    
    scan_results = {
        'stopped_instances': [
            {
                'ebs_monthly_cost': 10.0
            },
            {
                'ebs_monthly_cost': 15.0
            }
        ],
        'unattached_volumes': [
            {
                'monthly_cost': 20.0
            }
        ],
        'old_snapshots': [],
        'unassociated_eips': [
            {
                'monthly_cost': 3.6
            }
        ],
    }
    analyzer = CostAnalyzer()
    results = analyzer.calculate_total_waste(scan_results)

    assert results['estimated_waste']['stopped_ec2'] == 25.0
    assert results['estimated_waste']['unattached_ebs'] == 20.0
    assert results['estimated_waste']['old_snapshots'] == 0.0
    assert results['estimated_waste']['unassociated_eips'] == 3.6
    assert results['estimated_waste']['total'] == 48.6
    
    assert results['savings_potential']['monthly'] == 48.6
    assert results['savings_potential']['annual'] == 583.2 
    assert results['savings_potential']['percentage_of_bill'] == 24.3  
    
    assert results['actual_costs']['ec2_monthly'] == 100.0
    assert results['actual_costs']['ebs_monthly'] == 50.0
    assert results['actual_costs']['total_monthly'] == 200.0
    
    assert results['resource_counts']['stopped_instances'] == 2
    assert results['resource_counts']['unattached_volumes'] == 1
    assert results['resource_counts']['old_snapshots'] == 0
    assert results['resource_counts']['unassociated_eips'] == 1