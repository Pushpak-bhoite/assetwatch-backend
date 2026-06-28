"""
HTTP/HTTPS Checker

Monitors HTTP(S) endpoints by making GET requests.
Checks for successful status codes (2xx).
"""

import time
from typing import TYPE_CHECKING

import httpx

from worker.checkers.base import BaseChecker, CheckResult

if TYPE_CHECKING:
    from app.core.db import StandaloneMonitor


# Configuration
HTTP_TIMEOUT = 30  # seconds
USER_AGENT = "AssetWatch Monitor/1.0"


class HTTPChecker(BaseChecker):
    """
    HTTP/HTTPS endpoint checker.
    
    Performs GET requests and validates:
    - Connection successful
    - Response received within timeout
    - Status code is 2xx (success)
    """
    
    async def check(self, monitor: "StandaloneMonitor") -> CheckResult:
        """
        Check an HTTP(S) endpoint.
        
        Args:
            monitor: StandaloneMonitor with target URL
            
        Returns:
            CheckResult with success status and response time
        """
        url = monitor.target
        
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        start_time = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                )
                
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Check if status code indicates success (2xx)
            is_success = 200 <= response.status_code < 300
            
            if is_success:
                return CheckResult(
                    success=True,
                    response_time=elapsed_ms,
                    status_code=response.status_code,
                )
            else:
                return CheckResult(
                    success=False,
                    response_time=elapsed_ms,
                    error_message=f"HTTP {response.status_code}",
                    status_code=response.status_code,
                )
                
        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message="Connection timeout",
            )
            
        except httpx.ConnectError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"Connection failed: {str(e)[:100]}",
            )
            
        except httpx.HTTPError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"HTTP error: {str(e)[:100]}",
            )
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"Unexpected error: {str(e)[:100]}",
            )
