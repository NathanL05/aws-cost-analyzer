"""
AWS Cost Analyzer CLI - Main entry point.
"""
import click
from scanners.ec2_scanner import EC2Scanner
from scanners.ebs_scanner import EBSScanner
@click.group()
def cli():
    """AWS Cost Analyzer CLI"""
    pass 

@cli.command()
@click.option('--region', default='eu-west-1', help='AWS region to analyze')
def scan(region: str):
    """Scans AWS accounts for cost leaks"""
    click.echo(f"Scanning AWS account in region: {region}\n")

    click.echo("Scanning EC2 instances...")
    ec2_scanner = EC2Scanner(region=region)
    stopped_instances = ec2_scanner.scan_stopped_instances()

    ec2_waste = sum(i['ebs_monthly_cost'] for i in stopped_instances)
    click.echo(f"    Found {len(stopped_instances)} stopped EC2 instances")
    click.echo(f"    Potential waste: ${ec2_waste:.2f}\n")

    click.echo("Scanning EBS volumes...")
    ebs_scanner = EBSScanner(region=region)
    unattached_volumes = ebs_scanner.scan_unattached_volumes()

    ebs_waste = sum(v['monthly_cost'] for v in unattached_volumes)
    click.echo(f"    Found {len(unattached_volumes)} unattached EBS volumes")
    click.echo(f"    Potential waste: ${ebs_waste:.2f}\n")

    total_waste = ec2_waste + ebs_waste
    click.echo(f"Total potential savings: ${total_waste:.2f}")
    click.echo(f"Annual savings potential: ${total_waste * 12:.2f}")
if __name__ == '__main__':
    cli()