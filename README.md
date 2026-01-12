# AWS Cost Analyzer

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue.svg)

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

## 🐳 Docker Usage

### Quick Start with Docker

```bash
# Pull from Docker Hub (coming soon)
docker pull YOUR_USERNAME/aws-cost-analyzer:latest

# Run with AWS credentials from environment
docker run --rm \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION=eu-west-1 \
  aws-cost-analyzer:latest scan --region eu-west-1
```

### Build Locally

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/aws-cost-analyzer.git
cd aws-cost-analyzer

# Build optimized image
docker build -t aws-cost-analyzer:latest .

# Image size: ~150MB (multi-stage build)
```

### Development with Docker Compose

```bash
# Start development environment
docker-compose up -d

# Enter container for interactive development
docker-compose exec aws-cost-analyzer bash

# Inside container:
python cli.py scan --region eu-west-1
python -m pytest tests/ -v

# Stop environment
docker-compose down
```

### Docker Image Details

**Multi-stage build:**
- Stage 1 (builder): Installs dependencies, runs tests
- Stage 2 (runtime): Minimal image with only runtime requirements

**Security features:**
- Runs as non-root user (appuser)
- No build tools in final image
- Health check included

**Image size comparison:**
- Without multi-stage: ~500-600 MB
- With multi-stage: ~150-180 MB (70% reduction)

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

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User / CI/CD Pipeline                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Deployment Options                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Local Python │  │ Docker CLI   │  │ Kubernetes   │       │
│  │   (venv)     │  │  Container   │  │  CronJob     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
          ┌──────────────────────────────────────┐
          │      aws-cost-analyzer CLI           │
          │  ┌────────────┐  ┌────────────────┐  │
          │  │  Scanner   │  │   Analyzer     │  │
          │  │   Layer    │→ │    Layer       │  │
          │  └────────────┘  └────────────────┘  │
          └──────────┬───────────────────────────┘
                     │
       ┌─────────────┴─────────────┐
       │                           │
       ▼                           ▼
┌──────────────┐            ┌─────────────┐
│ AWS Services │            │   Reports   │
│ - EC2        │            │ - Console   │
│ - EBS        │            │ - JSON      │
│ - Snapshots  │            │ - CSV       │
│ - Elastic IP │            │             │
│ - Cost Expl. │            │             │
└──────────────┘            └─────────────┘
```

### Component Details

#### 1. Scanner Layer
- **EC2Scanner**: Detects stopped instances, calculates EBS costs
- **EBSScanner**: Finds unattached volumes, estimates waste
- **SnapshotScanner**: Identifies old snapshots (>90 days)
- **EIPScanner**: Finds unassociated Elastic IPs

#### 2. Analyzer Layer
- **CostExplorerAnalyzer**: Fetches actual AWS costs
- **CostAnalyzer**: Aggregates data, calculates savings potential

#### 3. Reporter Layer
- **ConsoleReporter**: Pretty tables for terminal output
- **JSONReporter**: Machine-readable export
- **CSVReporter**: Spreadsheet-compatible format

### Deployment Models

| Model | Use Case | Pros | Cons |
|-------|----------|------|------|
| Local Python | Development, testing | Fast iteration | Requires local setup |
| Docker CLI | One-off scans, portability | No dependencies | Manual execution |
| Kubernetes CronJob | Production, automation | Scheduled, scalable | Requires K8s cluster |

### Data Flow

```
1. User triggers scan (CLI/CronJob/CI)
2. Scanners query AWS APIs in parallel
3. Raw data passed to Analyzers
4. Cost calculations performed
5. Cost Explorer fetches actual bills
6. Reporters format output
7. Results displayed/exported
```

### Security Model

- **AWS Credentials**: Stored as K8s Secrets or environment variables
- **Container Security**: Non-root user, minimal base image
- **Network**: Read-only AWS API calls (no modifications)
- **Secrets Management**: Never committed to git

### Performance

- **Scan Time**: 10-30 seconds (varies by resource count)
- **API Calls**: ~10-20 per scan (uses pagination)
- **Memory**: <512MB peak
- **CPU**: <0.5 core average

### Project Structure

```
aws-cost-analyzer/
├── cli.py                   # Main CLI entry point
├── scanners/                # Resource scanners
│   ├── base_scanner.py      # Base class with caching & retry logic
│   ├── ec2_scanner.py       # Stopped EC2 instances
│   ├── ebs_scanner.py       # Unattached EBS volumes
│   ├── snapshot_scanner.py  # Old EBS snapshots
│   ├── eip_scanner.py       # Unassociated Elastic IPs
│   ├── iam_scanner.py       # Unused IAM access keys
│   ├── s3_scanner.py        # Unused S3 buckets
│   └── multi_region_scanner.py  # Multi-region scanning
├── analyzers/               # Cost analysis logic
│   ├── cost_analyzer.py     # Main analysis orchestrator
│   ├── cost_calculator.py   # Cost calculation utilities
│   └── cost_explorer.py     # AWS Cost Explorer integration
├── models/                  # Data models
│   └── leak.py              # Cost leak data structures
├── reporters/               # Output formatters
│   ├── json_reporter.py     # JSON export functionality
│   └── csv_reporter.py      # CSV export functionality
├── docs/                    # Documentation
│   └── architecture.md      # Detailed architecture docs
└── tests/                   # Unit tests
    ├── test_base_scanner_cache.py
    ├── test_ec2_scanner.py
    ├── test_ebs_scanner.py
    ├── test_snapshot_scanner.py
    ├── test_eip_scanner.py
    ├── test_iam_scanner.py
    ├── test_s3_scanner.py
    └── test_integration.py
```

## ⚡ Performance Benchmarks

### Caching Performance

The scanner implements a 5-minute TTL cache to reduce AWS API calls:

- **First scan:** ~5-10 seconds (depends on account size)
- **Cached scan:** ~0.1 seconds (100x faster)
- **Cache hit rate:** ~85% for repeated scans within 5 minutes

### Scan Times (Typical Account)

| Resource Type | First Scan | Cached Scan |
|--------------|------------|-------------|
| EC2 Instances | 2-3s | 0.05s |
| EBS Volumes | 1-2s | 0.03s |
| Snapshots | 3-5s | 0.08s |
| Elastic IPs | 0.5s | 0.02s |
| IAM Keys | 2-4s | N/A (global) |
| S3 Buckets | 1-2s | N/A (global) |
| **Total (6 scanners)** | **10-16s** | **~0.2s** |

### Multi-Region Performance

- **Sequential:** ~30-60 seconds per region × N regions
- **Parallel (5 workers):** ~10-15 seconds total for all regions
- **Recommended:** Use `--max-workers 5` for optimal throughput

### Retry Logic Performance

- **Transient errors:** Automatically retried with exponential backoff
- **Retry attempts:** 3 by default (configurable)
- **Backoff:** 1s, 2s, 4s intervals
- **Success rate:** 99%+ for transient AWS throttling errors

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Lint code
ruff check .

# Type checking
mypy scanners/ analyzers/ --ignore-missing-imports
```

## 🔧 Troubleshooting

### "Access Denied" Errors

**Problem:** Getting `AccessDenied` errors when scanning.

**Solutions:**
1. Check IAM permissions - you need read access to EC2, S3, and IAM:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:DescribeInstances",
           "ec2:DescribeVolumes",
           "ec2:DescribeSnapshots",
           "ec2:DescribeAddresses",
           "s3:ListBuckets",
           "s3:ListObjects",
           "iam:ListUsers",
           "iam:ListAccessKeys",
           "iam:GetAccessKeyLastUsed"
         ],
         "Resource": "*"
       }
     ]
   }
   ```
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Check if your AWS profile is set: `aws configure list`

### Cost Explorer Returns Empty

**Problem:** `--show-actual-costs` flag returns $0.00 or empty data.

**Solutions:**
- Cost Explorer takes **24 hours** to populate data after account creation
- Must use **us-east-1** region for Cost Explorer API (automatically handled)
- Ensure Cost Explorer is enabled in your AWS account
- Check billing permissions: `ce:GetCostAndUsage`

### Multi-Region Scan Fails for Some Regions

**Problem:** Some regions fail during `scan-all-regions` command.

**Solutions:**
- Some regions may not be enabled in your account
- Check enabled regions: `aws ec2 describe-regions`
- Enable regions in AWS Console if needed
- Temporary failures are handled gracefully (skipped with error message)

### Throttling Errors (429)

**Problem:** Getting throttled by AWS APIs during scans.

**Solutions:**
- The tool automatically retries with exponential backoff (3 attempts)
- Reduce `--max-workers` if scanning multiple regions: `--max-workers 3`
- Wait 5 minutes and run again (cache will help on second run)
- Consider scanning regions sequentially if throttling persists

### Cache Not Working

**Problem:** Scans taking full time even on repeated runs.

**Solutions:**
- Cache TTL is 5 minutes - wait at least 5 minutes between scans for cache benefit
- Cache is per-scanner instance - ensure you're using the same scanner object
- Check if cache is being cleared: `scanner._clear_cache()` (debug only)
- Multi-region scans don't share cache across regions (by design)

### Python Version Errors

**Problem:** `SyntaxError` or `TypeError` on older Python versions.

**Solutions:**
- Requires Python **3.11+** for type hints and modern features
- Check version: `python3 --version`
- Upgrade Python: `brew install python@3.11` (macOS) or use pyenv

### Docker: "Unable to locate credentials" Error

**Problem:** Getting `NoCredentialsError` when running Docker container.

**Solutions:**
1. **Set environment variables in your shell BEFORE running Docker:**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key_here
   export AWS_SECRET_ACCESS_KEY=your_secret_key_here
   export AWS_DEFAULT_REGION=eu-west-1
   ```

2. **Verify variables are set:**
   ```bash
   echo $AWS_ACCESS_KEY_ID  # Should show your key (not empty)
   echo $AWS_SECRET_ACCESS_KEY  # Should show your secret (not empty)
   ```

3. **Alternative: Pass credentials directly (less secure):**
   ```bash
   docker run --rm \
     -e AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE \
     -e AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
     -e AWS_DEFAULT_REGION=eu-west-1 \
     aws-cost-analyzer:latest scan --region eu-west-1
   ```

4. **Use AWS credentials file (if you have `~/.aws/credentials`):**
   ```bash
   # Mount AWS credentials directory
   docker run --rm \
     -v ~/.aws:/root/.aws:ro \
     -e AWS_PROFILE=default \
     aws-cost-analyzer:latest scan --region eu-west-1
   ```

**Common mistake:** Running `docker run -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID` when `$AWS_ACCESS_KEY_ID` is empty in your shell. Always `export` the variables first.

## ☸️ Kubernetes Deployment

Deploy aws-cost-analyzer to Kubernetes for automated daily scans with persistent result storage.

### Prerequisites

- kubectl installed and configured
- Kubernetes cluster running (minikube, EKS, GKE, or AKS)
- Docker image built
- AWS credentials configured

### Quick Start

```bash
# 1. Build and load image (for minikube)
docker build -t aws-cost-analyzer:v1.0 .
minikube image load aws-cost-analyzer:v1.0

# For EKS/GKE: Push to container registry
# docker tag aws-cost-analyzer:v1.0 YOUR_REGISTRY/aws-cost-analyzer:v1.0
# docker push YOUR_REGISTRY/aws-cost-analyzer:v1.0

# 2. Create AWS credentials secret
kubectl create secret generic aws-credentials \
  --from-literal=access-key-id=$AWS_ACCESS_KEY_ID \
  --from-literal=secret-access-key=$AWS_SECRET_ACCESS_KEY

# 3. Apply manifests
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/pvc.yaml
kubectl apply -f k8s/base/job.yaml

# 4. View scan results
kubectl logs -l app=aws-cost-analyzer
```

### Kubernetes Resources

The deployment includes:

- **ConfigMap** (`configmap.yaml`) - Environment configuration (region, thresholds)
- **PersistentVolumeClaim** (`pvc.yaml`) - 1GB storage for scan results
- **Job** (`job.yaml`) - One-time test scan
- **CronJob** (`cronjob.yaml`) - Automated daily scans at 9 AM UTC

### CronJob (Automated Daily Scans)

Enable daily automated scans with persistent result storage:

```bash
# Enable daily scans at 9 AM UTC
kubectl apply -f k8s/base/cronjob.yaml

# Check CronJob status
kubectl get cronjobs

# View job history
kubectl get jobs

# Manually trigger (don't wait for schedule)
kubectl create job --from=cronjob/aws-cost-analyzer-daily manual-test-$(date +%s)

# Wait for completion and view logs
kubectl wait --for=condition=complete --timeout=60s job/manual-test-<timestamp>
kubectl logs job/manual-test-<timestamp>
```

### View Historical Results

Scan results are saved to a PersistentVolume with date-stamped filenames:

```bash
# List all scan files
kubectl run -it --rm pvc-viewer --image=busybox --restart=Never --overrides='
{
  "spec": {
    "containers": [{
      "name": "pvc-viewer",
      "image": "busybox",
      "command": ["ls", "-lh", "/output"],
      "volumeMounts": [{"name": "output-volume", "mountPath": "/output"}]
    }],
    "volumes": [{
      "name": "output-volume",
      "persistentVolumeClaim": {"claimName": "cost-analyzer-output"}
    }]
  }
}'

# Read a specific scan result
kubectl run -it --rm pvc-reader --image=busybox --restart=Never --overrides='
{
  "spec": {
    "containers": [{
      "name": "pvc-reader",
      "image": "busybox",
      "command": ["cat", "/output/scan-20260111.json"],
      "volumeMounts": [{"name": "output-volume", "mountPath": "/output"}]
    }],
    "volumes": [{
      "name": "output-volume",
      "persistentVolumeClaim": {"claimName": "cost-analyzer-output"}
    }]
  }
}'
```

### Architecture Decision: Jobs vs Deployments

**Why Job/CronJob instead of Deployment?**

This CLI tool uses Kubernetes **Jobs** and **CronJobs**, not Deployments:

- ✅ **Jobs**: Run-to-completion workloads (scan completes and exits)
- ✅ **CronJobs**: Scheduled Jobs (daily scans at 9 AM UTC)
- ❌ **Deployments**: Long-running services (web servers, APIs)

**Why this matters:** Using a Deployment for a CLI tool that exits after completion causes **CrashLoopBackOff** because Kubernetes tries to keep restarting a process that's designed to finish.

### Resource Configuration

The CronJob includes production-ready resource limits:

```yaml
resources:
  requests:
    cpu: "250m"        # Minimum guaranteed CPU
    memory: "256Mi"    # Minimum guaranteed memory
  limits:
    cpu: "500m"        # Maximum CPU (throttled if exceeded)
    memory: "512Mi"    # Maximum memory (OOMKilled if exceeded)
```

**Why set limits?** Prevents pods from consuming excessive cluster resources and starving other workloads.

### Troubleshooting

#### ImagePullBackOff Error

**Problem:** Pod fails with `ImagePullBackOff` or `ErrImagePull`.

**Solution:**
```bash
# For minikube: Load image into minikube's Docker daemon
minikube image load aws-cost-analyzer:v1.0

# Verify image exists in minikube
minikube image ls | grep aws-cost-analyzer

# For EKS/GKE: Ensure image is pushed to registry and imagePullPolicy is correct
```

#### Secret Not Found Error

**Problem:** Pod fails with `Secret "aws-credentials" not found`.

**Solution:**
```bash
# Create the secret
kubectl create secret generic aws-credentials \
  --from-literal=access-key-id=$AWS_ACCESS_KEY_ID \
  --from-literal=secret-access-key=$AWS_SECRET_ACCESS_KEY

# Verify secret exists
kubectl get secret aws-credentials

# Verify secret has correct keys
kubectl describe secret aws-credentials
```

#### CronJob Not Running

**Problem:** CronJob doesn't create jobs at scheduled time.

**Solution:**
```bash
# Check CronJob status
kubectl get cronjobs
kubectl describe cronjob aws-cost-analyzer-daily

# Check schedule (should be "0 9 * * *" for 9 AM UTC)
kubectl get cronjob aws-cost-analyzer-daily -o yaml | grep schedule

# Check if CronJob is suspended
kubectl get cronjob aws-cost-analyzer-daily -o yaml | grep suspend

# For minikube: Ensure minikube is running
minikube status
```

#### View Pod Errors

**Problem:** Job fails but unsure why.

**Solution:**
```bash
# Get pod name
kubectl get pods -l app=aws-cost-analyzer

# View pod logs
kubectl logs <pod-name>

# View detailed pod state and events
kubectl describe pod <pod-name>

# View cluster events
kubectl get events --sort-by='.lastTimestamp' | grep cost-analyzer
```

### Production Considerations

For production deployments (EKS/GKE):

1. **Use IAM Roles for Service Accounts (IRSA)** instead of Secrets:
   - Eliminates need to store credentials in cluster
   - More secure (credentials rotated automatically)
   - AWS STS temporary credentials

2. **Use Helm charts** for easier version management:
   - Package all manifests together
   - Environment-specific values (dev/staging/prod)
   - Version control for deployments

3. **Add monitoring and alerting**:
   - Prometheus metrics for scan duration, resources found
   - Alerting if scan fails or finds costs above threshold
   - Grafana dashboards for cost trends

4. **Use Kustomize overlays** for environment-specific configs:
   - Base manifests for common configuration
   - Overlays for dev/staging/prod differences
   - Different schedules per environment

5. **Implement Pod Security Standards**:
   - Non-root user (already implemented in Dockerfile)
   - Read-only root filesystem where possible
   - Drop unnecessary capabilities

### Cleanup

```bash
# Delete all resources
kubectl delete cronjob aws-cost-analyzer-daily
kubectl delete job -l app=aws-cost-analyzer
kubectl delete pvc cost-analyzer-output
kubectl delete configmap aws-cost-analyzer-config
kubectl delete secret aws-credentials

# For minikube: Stop cluster
minikube stop

# For minikube: Delete cluster (removes all data)
minikube delete
```

## ❓ FAQ

### Why does scanning take so long?

First scans query AWS APIs which can take 10-16 seconds depending on account size. Subsequent scans within 5 minutes use cache and complete in ~0.2 seconds.

### How accurate are the cost estimates?

Costs are estimated based on AWS public pricing (as of 2024):
- **EBS volumes:** $0.08-0.125/GB-month (varies by type)
- **Snapshots:** $0.05/GB-month
- **Elastic IPs:** $3.60/month (fixed)
- Actual costs may vary by region and volume type. Use `--show-actual-costs` for real data.

### Can I run this in CI/CD?

Yes! The tool is designed to be non-destructive (read-only):
- No AWS resources are modified
- Safe to run in automated pipelines
- Returns exit code 0 on success, non-zero on errors

### Does this work with AWS Organizations?

Partially. The tool scans resources in the current AWS account/profile. For Organization-wide scanning, run it with appropriate cross-account IAM roles.

### How do I contribute a new scanner?

See [Contributing Guidelines](#-contributing) below. The pattern is straightforward:
1. Inherit from `BaseScanner`
2. Implement `scan_*` method
3. Add unit tests
4. Integrate in `cli.py`

### Is my AWS data sent anywhere?

No. This tool runs **locally** and only queries your AWS account via boto3. No data leaves your machine. All processing happens client-side.

## 📋 Requirements

- Python 3.11+
- AWS account with configured credentials
- IAM permissions:
  - `ec2:DescribeInstances`
  - `ec2:DescribeVolumes`
  - `ec2:DescribeSnapshots`
  - `ec2:DescribeAddresses`
  - `s3:ListBuckets`
  - `s3:ListObjects`
  - `iam:ListUsers`
  - `iam:ListAccessKeys`
  - `iam:GetAccessKeyLastUsed`
  - `ce:GetCostAndUsage` (optional, for actual costs)

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

Follow this pattern to add a new resource scanner:

1. **Create scanner file** in `scanners/` directory (e.g., `rds_scanner.py`)

2. **Inherit from BaseScanner:**
   ```python
   from .base_scanner import BaseScanner
   
   class RDSScanner(BaseScanner):
       def __init__(self, region: str = 'eu-west-1'):
           super().__init__(region)
           self.rds_client = boto3.client('rds', region_name=region)
   ```

3. **Implement scan method with caching:**
   ```python
   def scan_unused_db_instances(self, use_cache: bool = True) -> List[Dict[str, Any]]:
       cache_key = self._build_cache_key('unused_db_instances')
       
       if use_cache:
           cached = self._get_cached(cache_key)
           if cached is not None:
               return cached
       
       try:
           # Wrap AWS calls with retry logic
           response = self._retry_aws_call(
               lambda: self.rds_client.describe_db_instances()
           )
           
           results = []
           for db in response['DBInstances']:
               # Process and calculate costs
               results.append({...})
           
           if use_cache:
               self._set_cache(cache_key, results)
           
           return results
       except ClientError as e:
           self.handle_client_error(e, "scan_unused_db_instances")
           return []
   ```

4. **Add unit tests** in `tests/test_rds_scanner.py`:
   ```python
   def test_scan_unused_db_instances(mocker):
       # Mock boto3 client
       # Test caching
       # Test error handling
       pass
   ```

5. **Integrate in `cli.py`:**
   ```python
   from scanners.rds_scanner import RDSScanner
   
   @cli.command()
   def scan():
       rds_scanner = RDSScanner(region=region)
       results['unused_db'] = rds_scanner.scan_unused_db_instances()
   ```

### Code Standards

- **Type hints:** All functions must have type hints
- **Docstrings:** All public methods need docstrings
- **Error handling:** Use `_retry_aws_call()` for AWS API calls
- **Caching:** All scan methods should support `use_cache` parameter
- **Testing:** Minimum 80% code coverage
- **Linting:** Must pass `ruff check .` with no errors

## 🤝 Contributing

Contributions welcome! Here's how to contribute:

1. **Fork the repository**

2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-scanner-name
   ```

3. **Make your changes:**
   - Follow the code standards above
   - Add tests for new functionality
   - Update documentation

4. **Run tests and linting:**
   ```bash
   pytest tests/ -v
   ruff check .
   mypy scanners/ analyzers/ --ignore-missing-imports
   ```

5. **Commit your changes:**
   ```bash
   git commit -m "Add: New scanner for RDS instances"
   ```

6. **Push and create Pull Request**

### What We're Looking For

- New resource scanners (RDS, Lambda, CloudWatch Logs, etc.)
- Performance improvements
- Documentation improvements
- Bug fixes
- Test coverage improvements

### Code Review Process

1. All PRs require at least one approval
2. All tests must pass
3. Code coverage must not decrease
4. Linting must pass

## 📚 What I Learned

This project taught me:
- **boto3** - AWS SDK for Python with pagination patterns
- **click** - Building professional CLI tools
- **Production practices** - Type hints, docstrings, error handling
- **Cost optimization** - Understanding AWS pricing models
- **Testing** - Unit tests with mocks for AWS APIs

## 🔮 Future Enhancements

- [x] Multi-region scanning (scan all regions in parallel)
- [x] Cost Explorer API integration (actual cost data)
- [x] Caching with 5-minute TTL
- [x] Retry logic for transient AWS errors
- [x] GitHub Actions CI/CD pipeline
- [x] CSV export format
- [x] IAM access key scanning
- [x] S3 bucket scanning
- [x] Docker containerization (multi-stage builds, 70% size reduction)
- [ ] RDS instance analysis
- [ ] Lambda function analysis
- [ ] CloudWatch Logs analysis
- [ ] Slack/Email notifications
- [ ] Historical cost tracking
- [ ] Web dashboard

## 📝 License

MIT License - Free to use and modify

---

**If this tool helped you save money on AWS, consider starring the repo! ⭐**
