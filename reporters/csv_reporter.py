from typing import Any, Dict
import csv
import os

class CSVReporter:
    @staticmethod 
    def export_to_csv(scan_results: Dict[str, Any], filename: str) -> None:
        """Export scan results to a CSV file."""
        try:
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        except (OSError, TypeError):
            pass  
        
        try:
            with open(filename, 'w', newline='') as csvfile: 
                writer = csv.writer(csvfile)

                writer.writerow([
                    'Category', 'Resource ID', 'Details', 'Monthly Cost', 'Recommendation'
                ])

                for instance in scan_results.get('stopped_instances', []):
                    writer.writerow([
                        'Stopped EC2', 
                        instance['instance_id'],
                        f"Type: {instance['instance_type']}, Age: {instance['age_days']} days",
                        f"${instance['ebs_monthly_cost']:.2f}", 
                        instance['recommendation']
                    ])
                
                for volume in scan_results.get('unattached_volumes', []):
                    writer.writerow([
                        'Unattached EBS', 
                        volume['volume_id'],
                        f"Type: {volume['volume_type']}, Size: {volume['size']} GB",
                        f"${volume['monthly_cost']:.2f}",
                        volume['recommendation']
                    ])

                for snapshot in scan_results.get('old_snapshots', []):
                    writer.writerow([
                        'Old Snapshot', 
                        snapshot['snapshot_id'],
                        f"Size: {snapshot['size_gb']} GB, Age: {snapshot['age_days']} days",
                        f"${snapshot['monthly_cost']:.2f}",
                        snapshot['recommendation']
                    ])
                
                for eip in scan_results.get('unassociated_eips', []):
                    writer.writerow([
                        'Unassociated EIP', 
                        eip['allocation_id'],
                        f"IP: {eip['public_ip']}",
                        f"${eip['monthly_cost']:.2f}",
                        eip['recommendation']
                    ])
        except IOError as e:
            raise IOError(f"Failed to write CSV file '{filename}': {e}") from e
