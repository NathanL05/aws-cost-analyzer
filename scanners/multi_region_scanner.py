from typing import Dict, Any, List, Union
from scanners.ec2_scanner import EC2Scanner
from scanners.ebs_scanner import EBSScanner
from scanners.snapshot_scanner import SnapshotScanner
from scanners.eip_scanner import EIPScanner
from concurrent.futures import ThreadPoolExecutor, as_completed

class MultiRegionScanner:
    """Scanner for multiple AWS regions."""

    REGIONS = [
        'us-east-1',
        'us-west-1',
        'us-west-2',
        'eu-west-1',
        'eu-central-1',
        'ap-southeast-1',
        'ap-northeast-1',
    ]
    def scan_all_regions(self, max_workers: int = 5) -> Dict[str, Any]:
        """
        Scan all AWS regions in parallel. 

        Args:
            max_workers: Number of parallel threads

        Returns: 
            Results grouped by region
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_region = {
                executor.submit(self._scan_region, region): region for region in self.REGIONS
            }

            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    results[region] = future.result()
                except Exception as e:
                    print(f"Error scanning {region}: {e}")
                    results[region] = {
                        'stopped_instances': [],
                        'unattached_volumes': [],
                        'old_snapshots': [],
                        'unassociated_eips': [],
                        'error': str(e)
                    }

        return results



    def _scan_region(self, region: str) -> Dict[str, Union[List[Any], str]]:
        """Scan a single AWS region."""
        return {
            'stopped_instances': EC2Scanner(region).scan_stopped_instances(),
            'unattached_volumes': EBSScanner(region).scan_unattached_volumes(),
            'old_snapshots': SnapshotScanner(region).scan_old_snapshots(age_threshold_days=90),
            'unassociated_eips': EIPScanner(region).scan_unassociated_eips(),
        }