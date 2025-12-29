# AWS Cost Analyzer - Architecture

## System Overview

```
┌─────────────┐
│   User CLI  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         cli.py (Click)              │
│  - Parse arguments                  │
│  - Orchestrate scanners             │
│  - Format output                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│      Scanner Layer                  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │      BaseScanner              │  │
│  │  - Common initialization      │  │
│  │  - Error handling            │  │
│  └──────────────┬────────────────┘  │
│                 │ (inherits from)    │
│  ┌──────────────┴──────┐            │
│  │ EC2Scanner          │            │
│  │ EBSScanner          │            │
│  │ SnapshotScanner     │            │
│  │ EIPScanner          │            │
│  └─────────────────────┘            │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│      AWS APIs (boto3)               │
│  - describe_instances()             │
│  - describe_volumes()               │
│  - describe_snapshots()             │
│  - describe_addresses()             │
└─────────────────────────────────────┘
```

## Scanner Pattern

All scanners inherit from `BaseScanner`, which provides:
- Common initialization (region, ec2_client)
- Standardized error handling (`handle_client_error`)

Each scanner follows this pattern:

```python
from .base_scanner import BaseScanner

class ResourceScanner(BaseScanner):
    def __init__(self, region: str = 'eu-west-1'):
        super().__init__(region)  # Sets self.region and self.ec2_client
    
    def scan_resources(self) -> List[Dict[str, Any]]:
        try:
            # 1. Query AWS API (with pagination if needed)
            # 2. Process each resource
            # 3. Calculate costs
            # 4. Generate recommendations
            # 5. Return structured data
            return results
        except ClientError as e:
            self.handle_client_error(e, "scan_resources")
            return []
```

## Data Model

### Cost Leak Object

```python
{
    'resource_id': str,        # AWS resource identifier
    'resource_type': str,      # 'ec2', 'ebs', 'snapshot', 'eip'
    'monthly_cost': float,     # Estimated monthly cost in USD
    'age_days': int,           # How old the resource is
    'recommendation': str,     # Action to take
    'details': Dict[str, Any]  # Resource-specific metadata
}
```

## Cost Calculation

| Resource Type | Pricing Formula |
|--------------|-----------------|
| Stopped EC2  | Sum of attached EBS volumes × $0.08-0.10/GB |
| Unattached EBS | Volume size × $0.08-0.10/GB (by type) |
| Snapshots    | Size × $0.05/GB |
| Elastic IPs  | $0.005/hour = $3.60/month (fixed) |

## Future Architecture (Week 2-3)

```
CLI → Scanners → Analyzers → Reporters → Output
                    ↓
              Cost Analysis
              Prioritization
              Aggregation
```