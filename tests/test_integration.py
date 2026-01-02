"""Integration tests for AWS Cost Analyzer."""

from moto import mock_aws
import boto3
from scanners.ec2_scanner import EC2Scanner
from scanners.ebs_scanner import EBSScanner
from scanners.eip_scanner import EIPScanner
from scanners.snapshot_scanner import SnapshotScanner
from scanners.s3_scanner import S3Scanner
from freezegun import freeze_time
from datetime import datetime, timedelta

@mock_aws
def test_ec2_scanner_with_mock_aws():
    """Test EC2 scanner with mocked AWS."""
    ec2 = boto3.client('ec2', region_name='eu-west-1')

    response = ec2.run_instances(
        ImageId='ami-12345',
        MinCount=1, 
        MaxCount=1,
        InstanceType='t2.micro'
    )
    instance_id = response['Instances'][0]['InstanceId']

    ec2.stop_instances(InstanceIds=[instance_id])

    scanner = EC2Scanner(region='eu-west-1')
    results = scanner.scan_stopped_instances()

    assert len(results) == 1
    assert results[0]['instance_id'] == instance_id
    assert results[0]['instance_type'] == 't2.micro'
    assert results[0]['state'] == 'stopped'

@mock_aws
def test_ebs_scanner_with_mock_volumes():
    """Test EBS scanner with mocked volumes."""
    ec2 = boto3.client('ec2', region_name='eu-west-1')

    response = ec2.create_volume(
        AvailabilityZone='eu-west-1a',
        Size=100,
        VolumeType='gp3'
    )

    volume_id = response['VolumeId']

    scanner = EBSScanner(region='eu-west-1')
    results = scanner.scan_unattached_volumes()

    assert len(results) >= 1
    volume_ids = [v['volume_id'] for v in results]
    assert volume_id in volume_ids

@mock_aws
def test_eip_scanner_with_mock_unassociated_eips():
    """Test EIP scanner with mocked unassociated EIPs."""
    ec2 = boto3.client('ec2', region_name='eu-west-1')

    unused_eip1 = ec2.allocate_address(Domain='vpc')
    unused_eip2 = ec2.allocate_address(Domain='vpc')
    used_eip = ec2.allocate_address(Domain='vpc')

    instance = ec2.run_instances(
        ImageId='ami-12345',
        MinCount=1,
        MaxCount=1,
    )['Instances'][0]

    ec2.associate_address(
        InstanceId=instance['InstanceId'],
        AllocationId=used_eip['AllocationId']
    )

    scanner = EIPScanner(region='eu-west-1')
    results = scanner.scan_unassociated_eips()

    assert len(results) == 2
    eip_ids = [e['allocation_id'] for e in results]
    assert unused_eip1['AllocationId'] in eip_ids
    assert unused_eip2['AllocationId'] in eip_ids

@mock_aws
def test_snapshot_scanner_with_mock_old_snapshots():
    """Test Snapshot scanner with mocked old snapshots."""

    ec2 = boto3.client('ec2', region_name='eu-west-1')

    volume = ec2.create_volume(
        AvailabilityZone='eu-west-1a',
        Size=100,
        VolumeType='gp3'
    )['VolumeId']
    with freeze_time(datetime.now() - timedelta(days=100)):
        ec2.create_snapshot(
            VolumeId=volume,
            Description='Test snapshot',
        )['SnapshotId']

    scanner = SnapshotScanner(region='eu-west-1')
    results = scanner.scan_old_snapshots()

    assert len(results) == 1


@mock_aws
def test_s3_scanner_with_mock_buckets():
    """Test S3 scanner with mocked buckets."""
    s3 = boto3.client('s3', region_name='us-east-1')
    
    s3.create_bucket(Bucket='test-empty-bucket')
    
    s3.create_bucket(Bucket='test-full-bucket')
    s3.put_object(Bucket='test-full-bucket', Key='file.txt', Body=b'content')
    
    scanner = S3Scanner()
    results = scanner.scan_unused_buckets()
    
    bucket_names = [b['bucket_name'] for b in results]
    assert 'test-empty-bucket' in bucket_names




