"""
Monitor Checkers Package

Provides protocol-specific check implementations for different monitor types.

Checker Types:
- HTTPChecker: HTTP/HTTPS website/API monitoring
- PingChecker: ICMP ping monitoring
- PortChecker: TCP port monitoring
- DNSChecker: DNS record monitoring

Each checker implements the async `check()` method and returns a CheckResult.
"""

from worker.checkers.base import CheckResult
from worker.checkers.http import HTTPChecker
from worker.checkers.ping import PingChecker
from worker.checkers.port import PortChecker
from worker.checkers.dns import DNSChecker

# Map monitor types to their checkers
CHECKERS = {
    "http": HTTPChecker(),
    "ping": PingChecker(),
    "port": PortChecker(),
    "dns": DNSChecker(),
}


async def run_check(monitor) -> CheckResult:
    """
    Run the appropriate checker for a monitor.
    
    Args:
        monitor: StandaloneMonitor instance
        
    Returns:
        CheckResult with success status and details
    """
    checker = CHECKERS.get(monitor.monitor_type)
    
    if not checker:
        return CheckResult(
            success=False,
            response_time=0.0,
            error_message=f"Unknown monitor type: {monitor.monitor_type}",
        )
    
    return await checker.check(monitor)


__all__ = [
    "CheckResult",
    "HTTPChecker",
    "PingChecker",
    "PortChecker",
    "DNSChecker",
    "run_check",
]
