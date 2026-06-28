"""
TCP Port Checker

Monitors TCP port availability by attempting to establish a connection.
Checks if a specific port is open and accepting connections.
"""

import asyncio
import time
from typing import TYPE_CHECKING

from worker.checkers.base import BaseChecker, CheckResult

if TYPE_CHECKING:
    from app.core.db import StandaloneMonitor


# Configuration
PORT_TIMEOUT = 10  # seconds


class PortChecker(BaseChecker):
    """
    TCP Port checker.
    
    Attempts to establish a TCP connection to the specified port.
    If connection succeeds, the port is considered open/up.
    """
    
    async def check(self, monitor: "StandaloneMonitor") -> CheckResult:
        """
        Check if a TCP port is open.
        
        Args:
            monitor: StandaloneMonitor with target host and port
            
        Returns:
            CheckResult with success status and connection time
        """
        host = monitor.target
        port = monitor.port
        
        # Remove protocol if present
        if host.startswith(('http://', 'https://')):
            host = host.replace('http://', '').replace('https://', '').split('/')[0]
        
        if not port:
            return CheckResult(
                success=False,
                response_time=0.0,
                error_message="No port specified",
            )
        
        start_time = time.perf_counter()
        
        try:
            # Attempt to open a connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=PORT_TIMEOUT,
            )
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Close the connection
            writer.close()
            await writer.wait_closed()
            
            return CheckResult(
                success=True,
                response_time=elapsed_ms,
            )
            
        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"Connection timeout (port {port})",
            )
            
        except ConnectionRefusedError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"Connection refused (port {port})",
            )
            
        except OSError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            # Handle common errors
            if "Name or service not known" in str(e):
                error_msg = "Unknown host"
            elif "Network is unreachable" in str(e):
                error_msg = "Network unreachable"
            else:
                error_msg = f"Connection error: {str(e)[:80]}"
                
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=error_msg,
            )
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"Port check error: {str(e)[:80]}",
            )
