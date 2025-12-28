"""
AWS Cost Analyzer CLI - Main entry point.
"""
import click
from scanners.ec2_scanner import EC2Scanner
from scanners.ebs_scanner import EBSScanner
from scanners.eip_scanner import EIPScanner
from scanners.snapshot_scanner import SnapshotScanner
from tabulate import tabulate

@click.group()
def cli():
    """AWS Cost Analyzer CLI"""
    pass 

@cli.command()
@click.option('--region', default='eu-west-1', help='AWS region to analyze')
@click.option('--json-output', help='Save results to JSON file')
def scan(region: str, json_output: str):
    """Scans AWS accounts for cost leaks"""
    click.echo(f"Scanning AWS account in region: {region}\n")

    results = {}
    total_waste = 0.0
    
    click.echo("Scanning EC2 instances...")
    ec2_scanner = EC2Scanner(region=region)
    results['stopped_instances'] = ec2_scanner.scan_stopped_instances()
    ec2_waste = sum(i['ebs_monthly_cost'] for i in results['stopped_instances'])
    total_waste += ec2_waste
    click.echo(f"    Found {len(results['stopped_instances'])} stopped EC2 instances (${ec2_waste:.2f}/month)\n")

    click.echo("Scanning EBS volumes...")
    ebs_scanner = EBSScanner(region=region)
    results['unattached_volumes'] = ebs_scanner.scan_unattached_volumes()
    ebs_waste = sum(v['monthly_cost'] for v in results['unattached_volumes'])
    total_waste += ebs_waste
    click.echo(f"    Found {len(results['unattached_volumes'])} unattached EBS volumes (${ebs_waste:.2f}/month)\n")

    

    click.echo("Scanning snapshots...")
    snapshot_scanner = SnapshotScanner(region=region)
    results['old_snapshots'] = snapshot_scanner.scan_old_snapshots(age_threshold_days=90)
    snapshot_waste = sum(s['monthly_cost'] for s in results['old_snapshots'])
    total_waste += snapshot_waste
    click.echo(f"    Found {len(results['old_snapshots'])} old snapshots (>90 days old) (${snapshot_waste:.2f}/month)\n")
    
    click.echo("Scanning Elastic IPs...")
    eip_scanner = EIPScanner(region=region)
    results['unassociated_eips'] = eip_scanner.scan_unassociated_eips()
    eip_waste = sum(i['monthly_cost'] for i in results['unassociated_eips'])
    total_waste += eip_waste
    click.echo(f"    Found {len(results['unassociated_eips'])} unassociated Elastic IPs (${eip_waste:.2f}/month)\n")

    summary_data = [
        ['Stopped EC2 instances', len(results['stopped_instances']), f"${ec2_waste:.2f}/month"],
        ['Unattached EBS volumes', len(results['unattached_volumes']), f"${ebs_waste:.2f}/month"],
        ['Old snapshots (>90 days old)', len(results['old_snapshots']), f"${snapshot_waste:.2f}/month"],
        ['Unassociated Elastic IPs', len(results['unassociated_eips']), f"${eip_waste:.2f}/month"],
        ['', '', ''],
        ['TOTAL', '', f"${total_waste:.2f}"]
    ]

    click.echo("=" * 60)
    click.echo(tabulate(summary_data, headers=['Resource', 'Count', 'Monthly Cost'], tablefmt='grid'))
    click.echo("=" * 60)

    click.echo(f"\nTotal potential monthly savings: ${total_waste:.2f}")
    click.echo(f"Annual savings potential: ${total_waste * 12:.2f}")
    if json_output:
        import json 
        from datetime import datetime

        output_data = {
            'scan_date': datetime.now().isoformat(),
            'region': region,
            'total_monthly_savings': total_waste,
            'annual_savings': total_waste * 12,
            'results': results
        }

        with open(json_output, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        click.echo(f"Results saved to: {json_output}")

if __name__ == '__main__':
    cli()