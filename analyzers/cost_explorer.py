import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

class CostExplorerAnalyzer:
    def __init__(self):
        self.ce_client = boto3.client('ce', region_name='us-east-1')
    
    def get_monthly_cost_by_service(self, days: int) -> dict:
        """
        Get actual AWS costs by service for the last N days.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Dict mapping service names to costs
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': str(start_date),
                    'End': str(end_date)
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }] 
            )

            service_costs = {}
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service_name = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    service_costs[service_name] = service_costs.get(service_name, 0) + cost

            return service_costs
        except ClientError as e:
            print(f"Error getting cost and usage: {e}")
            return {}
    
    def get_ec2_actual_cost(self, days: int = 30) -> float:
        """Get the actual cost of EC2 instances for the last N days."""
        service_costs = self.get_monthly_cost_by_service(days)
        ec2_cost = service_costs.get('Amazon Elastic Compute Cloud - Compute', 0) 
        return round(ec2_cost, 2)

    def get_ebs_actual_cost(self, days: int = 30) -> float: 
        """
        Get the actual cost of EBS volumes for the last N days.
        
        Note: AWS Cost Explorer groups EBS costs under "EC2 - Other" or 
        "Amazon Elastic Compute Cloud - Compute", not as a separate service.
        This method attempts to find EBS costs but may return 0 if costs
        are bundled with EC2 compute costs.
        """
        service_costs = self.get_monthly_cost_by_service(days)

        ebs_keywords = ['Elastic Block Store', 'EBS', 'EC2 - Other']
        total_ebs = 0 

        for service_name, cost in service_costs.items():
            if any(keyword in service_name for keyword in ebs_keywords):
                total_ebs += cost
        
        return round(total_ebs, 2)
    
    def get_total_monthly_cost(self,  days: int = 30) -> float: 
        """Get the total monthly cost for the last N days."""
        service_costs = self.get_monthly_cost_by_service(days)
        return round(sum(service_costs.values()), 2)

