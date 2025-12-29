# AWS Cost Analyzer

A production-quality Python CLI tool that scans your AWS account for cost leaks and generates actionable recommendations to reduce your monthly bill.

## 🎯 What It Does

AWS Cost Analyzer identifies four major categories of cost waste:

1. **Stopped EC2 Instances** - Instances that aren't running but still charge for attached EBS volumes
2. **Unattached EBS Volumes** - Storage volumes not connected to any instance (100% waste)
3. **Old Snapshots** - EBS snapshots older than 90 days that accumulate storage costs
4. **Unassociated Elastic IPs** - Reserved IP addresses not attached to instances ($3.60/month each)

## 💰 Potential Savings

In a typical AWS account, this tool can identify:
- **10-30% reduction** in EBS storage costs
- **$50-500/month** in forgotten resources
- **Hundreds to thousands annually** for production accounts

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/aws-cost-analyzer.git
cd aws-cost-analyzer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: eu-west-1
```

### Run a Scan

```bash
# Scan default region
python3 cli.py scan

# Scan specific region
python3 cli.py scan --region us-east-1

# Export results to JSON
python3 cli.py scan --json-output results.json
```

## 📊 Example Output

```
🔍 Scanning AWS account in region: eu-west-1

📊 Scanning EC2 instances...
   Found 3 stopped instances ($24.00/month)

📊 Scanning EBS volumes...
   Found 5 unattached volumes ($50.00/month)

📊 Scanning EBS snapshots...
   Found 8 old snapshots (>90 days) ($40.00/month)

📊 Scanning Elastic IPs...
   Found 2 unassociated EIPs ($7.20/month)

============================================================
| Resource Type              | Count | Monthly Cost |
============================================================
| Stopped EC2 Instances      |     3 | $24.00       |
| Unattached EBS Volumes     |     5 | $50.00       |
| Old Snapshots (>90 days)   |     8 | $40.00       |
| Unassociated Elastic IPs   |     2 | $7.20        |
|                            |       |              |
| TOTAL                      |       | $121.20      |
============================================================

💰 Total potential monthly savings: $121.20
💰 Annual savings potential: $1,454.40
```

## 🏗️ Architecture

```
aws-cost-analyzer/
├── cli.py                   # Main CLI entry point
├── scanners/                # Resource scanners
│   ├── ec2_scanner.py       # Stopped EC2 instances
│   ├── ebs_scanner.py       # Unattached EBS volumes
│   ├── snapshot_scanner.py  # Old EBS snapshots
│   └── eip_scanner.py       # Unassociated Elastic IPs
├── analyzers/               # Cost analysis logic
│   └── cost_calculator.py   # Cost calculation utilities
├── models/                  # Data models
│   └── leak.py              # Cost leak data structures
├── reporters/               # Output formatters
│   └── json_reporter.py     # JSON export functionality
└── tests/                   # Unit tests
    ├── test_ec2_scanner.py
    ├── test_ebs_scanner.py
    ├── test_snapshot_scanner.py
    └── test_eip_scanner.py
```

### Data Flow

```
User Command → CLI → Scanners → AWS APIs → Process Results → Format Output → Display/Export
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=scanners --cov-report=html

# Lint code
ruff check .
```

## 📋 Requirements

- Python 3.11+
- AWS account with configured credentials
- IAM permissions:
  - `ec2:DescribeInstances`
  - `ec2:DescribeVolumes`
  - `ec2:DescribeSnapshots`
  - `ec2:DescribeAddresses`

## 🛠️ Development

### Running in Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt

# Run linter
ruff check . --fix

# Run tests with verbose output
pytest tests/ -v -s
```

### Adding a New Scanner

1. Create scanner file in `scanners/` directory
2. Implement scan method returning List[Dict[str, Any]]
3. Add unit tests in `tests/`
4. Import and integrate in `cli.py`

## 📚 What I Learned

This project taught me:
- **boto3** - AWS SDK for Python with pagination patterns
- **click** - Building professional CLI tools
- **Production practices** - Type hints, docstrings, error handling
- **Cost optimization** - Understanding AWS pricing models
- **Testing** - Unit tests with mocks for AWS APIs

## 🔮 Future Enhancements

- [ ] Multi-region scanning (scan all regions in parallel)
- [ ] Cost Explorer API integration (actual cost data)
- [ ] RDS instance analysis
- [ ] S3 bucket optimization
- [ ] Lambda function analysis
- [x] GitHub Actions CI/CD pipeline
- [ ] Docker containerization
- [ ] CSV export format
- [ ] Slack/Email notifications
- [ ] Historical cost tracking

## 📝 License

MIT License - Free to use and modify

---

**If this tool helped you save money on AWS, consider starring the repo! ⭐**
