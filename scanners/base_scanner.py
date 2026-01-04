"""Base scanner with common functionality."""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, Callable, TypeVar
from datetime import datetime, timedelta
import threading
import time

T = TypeVar('T')

class BaseScanner:
    """Base class for all resource scanners."""
    
    _cache: Dict[str, tuple] = {}
    _cache_lock = threading.Lock()
    _cache_ttl = timedelta(minutes=5)
    
    def __init__(self, region: str = 'eu-west-1'):
        """Initialize scanner with region."""
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Get cached result if still valid."""
        with self._cache_lock:
            if cache_key in self._cache:
                data, timestamp = self._cache[cache_key]
                age = datetime.now() - timestamp
                if age < self._cache_ttl:
                    return data
                else:
                    del self._cache[cache_key]
        return None
    
    def _build_cache_key(self, resource_type: str, **kwargs) -> str:
        """
        Build a cache key for a resource type.
        
        Format: 'region:resource_type:param1:value1:param2:value2'
        Parameters are sorted alphabetically for consistency.
        
        Args:
            resource_type: The type of resource (e.g., 'stopped_instances')
            **kwargs: Additional parameters to include in cache key
        
        Returns:
            Cache key string
        """
        key_parts = [self.region, resource_type]
        
        if kwargs:
            sorted_params = sorted(kwargs.items())
            for param_name, param_value in sorted_params:
                key_parts.append(str(param_name))
                key_parts.append(str(param_value))
        
        return ':'.join(key_parts)
    
    def _set_cache(self, cache_key: str, data: Any) -> None:
        """Cache results with timestamp."""
        with self._cache_lock:
            self._cache[cache_key] = (data, datetime.now())
    
    def _clear_cache(self, cache_key: Optional[str] = None) -> None:
        """
        Clear cache entries.
        
        Args:
            cache_key: If provided, clear only this key. If None, clear all cache.
        """
        with self._cache_lock:
            if cache_key is not None:
                self._cache.pop(cache_key, None)
            else:
                self._cache.clear()

    def _retry_aws_call(
        self, 
        func: Callable[[], T], 
        max_retries: int = 3, 
        delay: float = 1.0
    ) -> T:
        """
        Retry AWS API calls on transient errors with exponential backoff.
        
        Handles transient AWS errors like Throttling and ServiceUnavailable
        by retrying with exponential backoff. Non-retryable errors are
        immediately re-raised.
        
        Args:
            func: A callable that performs the AWS API call
            max_retries: Maximum number of retry attempts (default: 3)
            delay: Initial delay in seconds before retry (default: 1.0)
        
        Returns:
            The result of the AWS API call
        
        Raises:
            ClientError: If all retries are exhausted or error is not retryable
        """
        retryable_errors = ['Throttling', 'ServiceUnavailable', 'RequestLimitExceeded']
        
        last_exception: Optional[ClientError] = None
        for attempt in range(max_retries):
            try:
                return func()
            except ClientError as e:
                last_exception = e
                error_code = e.response['Error']['Code']
                
                if error_code in retryable_errors and attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  
                    time.sleep(wait_time)
                    continue
                raise
        
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic failed unexpectedly")

    def handle_client_error(self, error: ClientError, context: str) -> None:
        """Standard error handling for boto3 ClientError."""
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        print(f"Error in {context}: [{error_code}] {error_message}")
