"""Tests for BaseScanner caching functionality."""

from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from scanners.base_scanner import BaseScanner


class TestCacheKeyBuilding:
    """Test cache key generation."""
    
    def test_build_cache_key_basic(self):
        """Test basic cache key with region and resource type."""
        scanner = BaseScanner(region='eu-west-1')
        key = scanner._build_cache_key('stopped_instances')
        assert key == 'eu-west-1:stopped_instances'
    
    def test_build_cache_key_with_params(self):
        """Test cache key with additional parameters."""
        scanner = BaseScanner(region='us-east-1')
        key = scanner._build_cache_key('old_snapshots', age_threshold=90)
        assert key == 'us-east-1:old_snapshots:age_threshold:90'
    
    def test_build_cache_key_multiple_params(self):
        """Test cache key with multiple parameters (sorted)."""
        scanner = BaseScanner(region='eu-west-1')
        key = scanner._build_cache_key('resources', param_b=2, param_a=1)
        assert 'param_a:1' in key
        assert 'param_b:2' in key
        assert key.startswith('eu-west-1:resources:')


class TestCacheOperations:
    """Test cache get/set/clear operations."""
    
    def setup_method(self):
        """Clear cache before each test."""
        BaseScanner._cache.clear()
    
    def test_set_and_get_cache(self):
        """Test setting and getting cached data."""
        scanner = BaseScanner(region='eu-west-1')
        cache_key = 'test_key'
        test_data = {'instances': [1, 2, 3]}
        
        assert scanner._get_cached(cache_key) is None
        
        scanner._set_cache(cache_key, test_data)
        
        cached = scanner._get_cached(cache_key)
        assert cached == test_data
    
    def test_cache_expiration(self):
        """Test that expired cache entries return None."""
        scanner = BaseScanner(region='eu-west-1')
        cache_key = 'test_key'
        test_data = {'data': 'test'}
        
        with BaseScanner._cache_lock:
            BaseScanner._cache[cache_key] = (
                test_data,
                datetime.now() - timedelta(minutes=10)
            )
        
        assert scanner._get_cached(cache_key) is None
        
        assert cache_key not in BaseScanner._cache
    
    def test_cache_per_region(self):
        """Test that different regions have separate cache entries."""
        scanner_eu = BaseScanner(region='eu-west-1')
        scanner_us = BaseScanner(region='us-east-1')
        
        key_eu = scanner_eu._build_cache_key('stopped_instances')
        key_us = scanner_us._build_cache_key('stopped_instances')
        
        assert key_eu != key_us
        
        scanner_eu._set_cache(key_eu, {'region': 'eu-west-1'})
        
        assert scanner_us._get_cached(key_us) is None
        assert scanner_eu._get_cached(key_eu) is not None
    
    def test_clear_specific_cache_key(self):
        """Test clearing a specific cache entry."""
        scanner = BaseScanner(region='eu-west-1')
        
        key1 = 'key1'
        key2 = 'key2'
        
        scanner._set_cache(key1, {'data': 1})
        scanner._set_cache(key2, {'data': 2})
        
        scanner._clear_cache(key1)
        
        assert scanner._get_cached(key1) is None
        assert scanner._get_cached(key2) is not None
    
    def test_clear_all_cache(self):
        """Test clearing all cache entries."""
        scanner = BaseScanner(region='eu-west-1')
        
        scanner._set_cache('key1', {'data': 1})
        scanner._set_cache('key2', {'data': 2})
        
        scanner._clear_cache()
        
        assert scanner._get_cached('key1') is None
        assert scanner._get_cached('key2') is None
        assert len(BaseScanner._cache) == 0


class TestCacheInScannerUsage:
    """Test caching in actual scanner usage (EC2Scanner example)."""
    
    def setup_method(self):
        """Clear cache before each test."""
        BaseScanner._cache.clear()
    
    @patch('scanners.ec2_scanner.boto3.client')
    @patch('scanners.ec2_scanner.boto3.resource')
    def test_ec2_scanner_cache_hit(self, mock_resource, mock_client):
        """Test that EC2Scanner uses cache on second call."""
        from scanners.ec2_scanner import EC2Scanner
        
        mock_ec2_client = Mock()
        mock_client.return_value = mock_ec2_client
        
        mock_paginator = Mock()
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Reservations': []}]
        
        mock_ec2_resource = Mock()
        mock_resource.return_value = mock_ec2_resource
        
        scanner = EC2Scanner(region='eu-west-1')
        
        result1 = scanner.scan_stopped_instances(use_cache=True)
        assert mock_ec2_client.get_paginator.call_count == 1
        
        result2 = scanner.scan_stopped_instances(use_cache=True)
        assert mock_ec2_client.get_paginator.call_count == 1  
        assert result1 == result2
    
    @patch('scanners.ec2_scanner.boto3.client')
    @patch('scanners.ec2_scanner.boto3.resource')
    def test_ec2_scanner_cache_bypass(self, mock_resource, mock_client):
        """Test that use_cache=False bypasses cache."""
        from scanners.ec2_scanner import EC2Scanner
        
        mock_ec2_client = Mock()
        mock_client.return_value = mock_ec2_client
        
        mock_paginator = Mock()
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Reservations': []}]
        
        mock_ec2_resource = Mock()
        mock_resource.return_value = mock_ec2_resource
        
        scanner = EC2Scanner(region='eu-west-1')
        
        scanner.scan_stopped_instances(use_cache=True)
        assert mock_ec2_client.get_paginator.call_count == 1

        scanner.scan_stopped_instances(use_cache=False)
        assert mock_ec2_client.get_paginator.call_count == 2


class TestCacheThreadSafety:
    """Test that cache operations are thread-safe."""
    
    def setup_method(self):
        """Clear cache before each test."""
        BaseScanner._cache.clear()
    
    def test_concurrent_cache_access(self):
        """Test that multiple threads can safely access cache."""
        import threading
        
        scanner = BaseScanner(region='eu-west-1')
        cache_key = 'test_key'
        results = []
        
        def set_cache():
            scanner._set_cache(cache_key, {'thread': threading.current_thread().name})
            results.append(scanner._get_cached(cache_key))
        
        threads = [threading.Thread(target=set_cache) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(results) == 10
        assert len(BaseScanner._cache) == 1
