import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError

class EIPScanner:
    def __init__(self, region: str = 'eu-west-1'):
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)

    def scan_unassociated_eips(self) -> List[Dict[str, Any]]:
        """
        Scan for unassociated EIPs
        """ 
        try:
            response = self.ec2_client.describe_addresses()

            unassociated_eips = []
            for address in response['Addresses']:
                if address.get('AssociationId') is None:
                    eip_data = self._process_unassociated_eip(address)
                    unassociated_eips.append(eip_data)
            return unassociated_eips
        except ClientError as e:
            print(f"Error scanning EIPs: {e}")
            return []

    def _process_unassociated_eip(self, address: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an unassociated EIP
        """ 
        allocation_id = address.get('AllocationId', 'unknown')
        public_ip = address.get('PublicIp', 'unknown')

        monthly_cost = 3.60

        return {
            'allocation_id': allocation_id,
            'public_ip': public_ip,
            'monthly_cost': monthly_cost,
            'recommendation': f"RELEASE - Unassociated EIP wasting ${monthly_cost:.2f}/month"
        }
