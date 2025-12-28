# AWS Cost Analyzer

A Python CLI tool that scans AWS accounts for cost leaks and unused resources. Identifies stopped EC2 instances, unattached EBS volumes, old snapshots, and unassociated Elastic IPs.

## Features

- **EC2 Scanner**: Finds stopped instances with attached EBS volumes
- **EBS Scanner**: Identifies unattached volumes
- **Snapshot Scanner**: Detects old snapshots (>90 days) and orphaned snapshots
- **Elastic IP Scanner**: Finds unassociated Elastic IPs costing $3.60/month
- **Pretty Output**: Tabular summary with cost breakdown
- **JSON Export**: Export results for automation/reporting

## Prerequisites

- Python 3.9+
- AWS credentials configured (via `~/.aws/credentials` or environment variables)
- AWS IAM permissions for EC2 read operations

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd aws-cost-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Scan

Scan your AWS account in a specific region:
```bash
python3 cli.py scan --region eu-west-1
```

### Export to JSON

Save results to a JSON file:
```bash
python3 cli.py scan --region eu-west-1 --json-output results.json
```

### Help

```bash
python3 cli.py --help
python3 cli.py scan --help
```

## Example Output

```
Scanning AWS account in region: eu-west-1

Scanning EC2 instances...
    Found 2 stopped EC2 instances ($15.60/month)

Scanning EBS volumes...
    Found 3 unattached EBS volumes ($2.40/month)

Scanning snapshots...
    Found 5 old snapshots (>90 days old) ($1.25/month)

Scanning Elastic IPs...
    Found 1 unassociated Elastic IPs ($3.60/month)

============================================================
| Resource                  | Count | Monthly Cost          |
============================================================
| Stopped EC2 instances     |   2   | $15.60/month          |
| Unattached EBS volumes    |   3   | $2.40/month           |
| Old snapshots (>90 days)  |   5   | $1.25/month           |
| Unassociated Elastic IPs  |   1   | $3.60/month           |
|                           |       |                       |
| TOTAL                     |       | $22.85                |
============================================================

Total potential monthly savings: $22.85
Annual savings potential: $274.20
```

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

## Project Structure

```
aws-cost-analyzer/
├── cli.py                 # Main CLI entry point
├── scanners/              # Resource scanners
│   ├── ec2_scanner.py
│   ├── ebs_scanner.py
│   ├── eip_scanner.py
│   └── snapshot_scanner.py
├── tests/                 # Unit tests
└── requirements.txt       # Dependencies
```

## License

MIT
