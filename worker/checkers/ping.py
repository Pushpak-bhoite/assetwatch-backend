"""
Ping (ICMP) Checker

Monitors host availability using ICMP ping.
Uses system ping command via subprocess for cross-platform compatibility.

Note: Raw ICMP sockets require root privileges, so we use the system ping
command which handles this properly on most systems.
"""

import asyncio
import platform
import re
import time
from typing import TYPE_CHECKING, Optional, Tuple

from worker.checkers.base import BaseChecker, CheckResult

if TYPE_CHECKING:
    from app.core.db import StandaloneMonitor


# Configuration
PING_TIMEOUT = 10  # seconds
PING_COUNT = 1  # Number of pings to send


class PingChecker(BaseChecker):
    """
    ICMP Ping checker using system ping command.
    
    Sends a single ping and checks for response.
    Extracts response time from ping output.
    """
    
    async def check(self, monitor: "StandaloneMonitor") -> CheckResult:
        """
        Ping a host.
        
        Args:
            monitor: StandaloneMonitor with target host/IP
            
        Returns:
            CheckResult with success status and response time
        """
        host = monitor.target
        
        # Remove protocol if present
        if host.startswith(('http://', 'https://')):
            host = host.replace('http://', '').replace('https://', '').split('/')[0]
        
        start_time = time.perf_counter()
        
        try:
            success, response_time, error = await self._execute_ping(host)
            
            if success:
                return CheckResult(
                    success=True,
                    response_time=response_time or (time.perf_counter() - start_time) * 1000,
                )
            else:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return CheckResult(
                    success=False,
                    response_time=elapsed_ms,
                    error_message=error or "Ping failed",
                )
                
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"Ping error: {str(e)[:100]}",
            )
    
    async def _execute_ping(self, host: str) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Execute the system ping command.
        
        Args:
            host: Hostname or IP to ping
            
        Returns:
            Tuple of (success, response_time_ms, error_message)
        """
        # Build ping command based on OS
        if platform.system().lower() == "windows":
            # Windows: ping -n 1 -w timeout_ms hostname
            cmd = ["ping", "-n", str(PING_COUNT), "-w", str(PING_TIMEOUT * 1000), host]
        else:
            # Linux/macOS: ping -c 1 -W timeout hostname
            cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT), host]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=PING_TIMEOUT + 5  # Extra buffer for process
            )
            
            output = stdout.decode('utf-8', errors='ignore')
            
            # Check if ping was successful
            if process.returncode == 0:
                # Extract response time from output
                response_time = self._parse_response_time(output)
                return (True, response_time, None)
            else:
                # Ping failed
                error_output = stderr.decode('utf-8', errors='ignore').strip()
                if "unknown host" in output.lower() or "could not find host" in output.lower():
                    return (False, None, "Unknown host")
                elif "request timed out" in output.lower() or "100% packet loss" in output.lower():
                    return (False, None, "Request timed out")
                else:
                    return (False, None, error_output[:100] if error_output else "Host unreachable")
                    
        except asyncio.TimeoutError:
            return (False, None, "Ping timeout")
    
    def _parse_response_time(self, output: str) -> Optional[float]:
        """
        Parse response time from ping output.
        
        Handles different formats:
        - Linux/macOS: time=X.XX ms
        - Windows: time=Xms or time<1ms
        
        Args:
            output: Ping command stdout
            
        Returns:
            Response time in milliseconds, or None if not found
        """
        # Try to match "time=X.XX ms" or "time=Xms"
        patterns = [
            r'time[=<](\d+\.?\d*)\s*ms',  # time=1.23 ms or time=1ms
            r'(\d+\.?\d*)\s*ms',  # fallback: just find X.XX ms
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
