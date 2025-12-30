"""
AWS Cost Analyzer CLI - Main entry point.
"""
import click
from scanners.ec2_scanner import EC2Scanner
from scanners.ebs_scanner import EBSScanner
from scanners.eip_scanner import EIPScanner
from scanners.snapshot_scanner import SnapshotScanner
from tabulate import tabulate
from analyzers.cost_analyzer import CostAnalyzer
from typing import Dict, Any

@click.group()
def cli():
    """AWS Cost Analyzer CLI"""
    pass 

@cli.command()
@click.option('--region', default='eu-west-1', help='AWS region to analyze')
@click.option('--json-output', help='Save results to JSON file')
@click.option('--show-actual-costs', is_flag=True, help='Fetch actual costs from Cost Explorer')
def scan(region: str, json_output: str, show_actual_costs: bool):
    """Scans AWS accounts for cost leaks"""
    click.echo(f"🔍 Scanning AWS account in region: {region}\n")

    results = {}
    total_waste = 0.0
    
    click.echo("📊 Scanning EC2 instances...")
    ec2_scanner = EC2Scanner(region=region)
    results['stopped_instances'] = ec2_scanner.scan_stopped_instances()
    ec2_waste = sum(i['ebs_monthly_cost'] for i in results['stopped_instances'])
    total_waste += ec2_waste
    click.echo(f"    ✅ Found {len(results['stopped_instances'])} stopped EC2 instances (${ec2_waste:.2f}/month)\n")

    click.echo("📊 Scanning EBS volumes...")
    ebs_scanner = EBSScanner(region=region)
    results['unattached_volumes'] = ebs_scanner.scan_unattached_volumes()
    ebs_waste = sum(v['monthly_cost'] for v in results['unattached_volumes'])
    total_waste += ebs_waste
    click.echo(f"    ✅ Found {len(results['unattached_volumes'])} unattached EBS volumes (${ebs_waste:.2f}/month)\n")


    click.echo("📊 Scanning snapshots...")
    snapshot_scanner = SnapshotScanner(region=region)
    results['old_snapshots'] = snapshot_scanner.scan_old_snapshots(age_threshold_days=90)
    snapshot_waste = sum(s['monthly_cost'] for s in results['old_snapshots'])
    total_waste += snapshot_waste
    click.echo(f"    ✅ Found {len(results['old_snapshots'])} old snapshots (>90 days old) (${snapshot_waste:.2f}/month)\n")
    
    click.echo("📊 Scanning Elastic IPs...")
    eip_scanner = EIPScanner(region=region)
    results['unassociated_eips'] = eip_scanner.scan_unassociated_eips()
    eip_waste = sum(i['monthly_cost'] for i in results['unassociated_eips'])
    total_waste += eip_waste
    click.echo(f"    ✅ Found {len(results['unassociated_eips'])} unassociated Elastic IPs (${eip_waste:.2f}/month)\n")

    if show_actual_costs:
        click.echo("💵 Fetching actual costs from Cost Explorer...")

    analyzer = CostAnalyzer()
    analysis = analyzer.calculate_total_waste(results)
    
    _display_analysis(analysis, show_actual_costs)

    if json_output:
        _export_json(results, analysis, region, json_output)


def _display_analysis(analysis: Dict[str, Any], show_actual: bool):
    """Display the analysis of the scan results."""
    estimated = analysis['estimated_waste']

    waste_data = [
        ['🖥️  Stopped EC2 Instances', f"${estimated['stopped_ec2']:.2f}"],
        ['💾 Unattached EBS Volumes', f"${estimated['unattached_ebs']:.2f}"],
        ['📸 Old Snapshots (>90 days old)', f"${estimated['old_snapshots']:.2f}"],
        ['🌐 Unassociated Elastic IPs', f"${estimated['unassociated_eips']:.2f}"],
        ['', ''],
        ['⚠️  TOTAL WASTE', f"${estimated['total']:.2f}"],
    ]

    click.echo("=" * 60)
    click.echo(tabulate(waste_data, headers=['Category', 'Monthly Cost'], tablefmt='grid'))
    click.echo("=" * 60)

    if show_actual:
        actual = analysis['actual_costs']
        savings = analysis['savings_potential']
    
        click.echo("\n💵 Actual AWS Costs (Last 30 Days):")
        click.echo(f"   Total Monthly Bill: ${actual['total_monthly']:.2f}")
        click.echo(f"   EC2 Costs: ${actual['ec2_monthly']:.2f}")
        click.echo(f"   EBS Costs: ${actual['ebs_monthly']:.2f}")
        
        if actual['total_monthly'] > 0:
            click.echo("\n💰 Savings Analysis:")
            click.echo(f"   Potential Monthly Savings: ${savings['monthly']:.2f}")
            click.echo(f"   Potential Annual Savings: ${savings['annual']:.2f}")
            click.echo(f"   Percentage of Bill: {savings['percentage_of_bill']:.1f}%")
        else:
            click.echo(f"\n💰 Potential Monthly Savings: ${estimated['total']:.2f}")
            click.echo(f"💰 Potential Annual Savings: ${estimated['total'] * 12:.2f}")
            click.echo("\n   ℹ️  Note: Actual AWS bill is $0.00 (Free Tier or no usage)")
    else:
        click.echo(f"\n💰 Potential Monthly Savings: ${estimated['total']:.2f}")
        click.echo(f"💰 Potential Annual Savings: ${estimated['total'] * 12:.2f}")


def _export_json(scan_results: Dict[str, Any], analysis: Dict[str, Any], region: str, filename: str): 
    """Export results to JSON file."""
    import json 
    from datetime import datetime

    output_data = {
        'scan_date': datetime.now().isoformat(),
        'region': region, 
        'analysis': analysis,
        'scan_results': scan_results
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    click.echo(f"💾 Results saved to: {filename}")

if __name__ == '__main__':
    cli()