from .cost_explorer import CostExplorerAnalyzer
from typing import Dict, Any, List

class CostAnalyzer:
    def __init__(self):
        """Initialize the CostAnalyzer."""
        self.cost_explorer = CostExplorerAnalyzer()

    def calculate_total_waste(self, scan_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Calculate the total waste based on the scan results.

        Args:
            scan_results: A dictionary containing the scan results.

        Returns:
            A dictionary containing the total waste.
        """

        ec2_waste = sum(
            i.get('ebs_monthly_cost', 0)
            for i in scan_results.get('stopped_instances', [])
        )

        ebs_waste = sum(
            i.get('monthly_cost', 0)
            for i in scan_results.get('unattached_volumes', [])
        )

        snapshot_waste = sum(
            i.get('monthly_cost', 0)
            for i in scan_results.get('old_snapshots', [])
        )

        eip_waste = sum(
            i.get('monthly_cost', 0)
            for i in scan_results.get('unassociated_eips', [])
        )
        
        total_estimated_waste = ec2_waste + ebs_waste + snapshot_waste + eip_waste

        try:
            actual_ec2_cost = self.cost_explorer.get_ec2_actual_cost(days=30)
            actual_ebs_cost = self.cost_explorer.get_ebs_actual_cost(days=30)
            total_monthly_cost = self.cost_explorer.get_total_monthly_cost(days=30)
        except Exception as e:
            print(f"Error getting actual costs: {e}")
            actual_ec2_cost = 0
            actual_ebs_cost = 0
            total_monthly_cost = 0
        
        return {
            'estimated_waste': {
                'stopped_ec2': round(ec2_waste, 2),
                'unattached_ebs': round(ebs_waste, 2),
                'old_snapshots': round(snapshot_waste, 2),
                'unassociated_eips': round(eip_waste, 2),
                'total': round(total_estimated_waste, 2)
            },
            'actual_costs': {
                'ec2_monthly': actual_ec2_cost,
                'ebs_monthly': actual_ebs_cost,
                'total_monthly': total_monthly_cost
            },
            'savings_potential': {
                'monthly': round(total_estimated_waste, 2),
                'annual': round(total_estimated_waste * 12, 2),
                'percentage_of_bill': round(
                    (total_estimated_waste / total_monthly_cost * 100) if total_monthly_cost > 0 else 0, 1
                )
            }, 
            'resource_counts': {
                'stopped_instances': len(scan_results.get('stopped_instances', [])),
                'unattached_volumes': len(scan_results.get('unattached_volumes', [])),
                'old_snapshots': len(scan_results.get('old_snapshots', [])),
                'unassociated_eips': len(scan_results.get('unassociated_eips', [])),
            }
        }