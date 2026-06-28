"""
DNS Checker

Monitors DNS resolution by performing DNS queries.
Supports A, AAAA, CNAME, MX, TXT, NS, SOA record types.
Optionally validates expected values.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Optional, List

import dns.asyncresolver
import dns.resolver
import dns.exception

from worker.checkers.base import BaseChecker, CheckResult

if TYPE_CHECKING:
    from app.core.db import StandaloneMonitor


# Configuration
DNS_TIMEOUT = 10  # seconds


class DNSChecker(BaseChecker):
    """
    DNS record checker.
    
    Performs DNS queries and optionally validates:
    - Record resolution succeeds
    - Resolved value matches expected value (if specified)
    """
    
    async def check(self, monitor: "StandaloneMonitor") -> CheckResult:
        """
        Check DNS resolution for a hostname.
        
        Args:
            monitor: StandaloneMonitor with target hostname and DNS settings
            
        Returns:
            CheckResult with success status and resolved value
        """
        hostname = monitor.target
        record_type = (monitor.record_type or "A").upper()
        expected_value = monitor.expected_value
        dns_server = monitor.dns_server
        
        # Remove protocol if present
        if hostname.startswith(('http://', 'https://')):
            hostname = hostname.replace('http://', '').replace('https://', '').split('/')[0]
        
        start_time = time.perf_counter()
        
        try:
            # Create resolver
            resolver = dns.asyncresolver.Resolver()
            resolver.timeout = DNS_TIMEOUT
            resolver.lifetime = DNS_TIMEOUT
            
            # Configure custom DNS server if specified
            if dns_server:
                resolver.nameservers = [dns_server]
            
            # Perform DNS query
            answers = await asyncio.wait_for(
                resolver.resolve(hostname, record_type),
                timeout=DNS_TIMEOUT,
            )
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract resolved values
            resolved_values = self._extract_values(answers, record_type)
            resolved_str = ", ".join(resolved_values) if resolved_values else None
            
            # Validate expected value if specified
            if expected_value:
                if not self._validate_expected(resolved_values, expected_value):
                    return CheckResult(
                        success=False,
                        response_time=elapsed_ms,
                        error_message=f"Expected '{expected_value}', got '{resolved_str}'",
                        resolved_value=resolved_str,
                    )
            
            return CheckResult(
                success=True,
                response_time=elapsed_ms,
                resolved_value=resolved_str,
            )
            
        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message="DNS query timeout",
            )
            
        except dns.resolver.NXDOMAIN:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message="Domain does not exist (NXDOMAIN)",
            )
            
        except dns.resolver.NoAnswer:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"No {record_type} record found",
            )
            
        except dns.resolver.NoNameservers:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message="No nameservers available",
            )
            
        except dns.exception.DNSException as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"DNS error: {str(e)[:80]}",
            )
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                success=False,
                response_time=elapsed_ms,
                error_message=f"DNS check error: {str(e)[:80]}",
            )
    
    def _extract_values(self, answers, record_type: str) -> List[str]:
        """
        Extract string values from DNS answer records.
        
        Args:
            answers: DNS answer set
            record_type: The type of record queried
            
        Returns:
            List of resolved values as strings
        """
        values = []
        
        for rdata in answers:
            if record_type == "MX":
                # MX records have preference and exchange
                values.append(f"{rdata.preference} {rdata.exchange}")
            elif record_type == "TXT":
                # TXT records may be split across multiple strings
                values.append("".join(s.decode('utf-8', errors='ignore') for s in rdata.strings))
            elif record_type == "SOA":
                # SOA records have multiple fields
                values.append(f"{rdata.mname} {rdata.rname}")
            else:
                # A, AAAA, CNAME, NS
                values.append(str(rdata))
        
        return values
    
    def _validate_expected(self, resolved_values: List[str], expected: str) -> bool:
        """
        Validate if resolved values contain the expected value.
        
        Args:
            resolved_values: List of resolved DNS values
            expected: Expected value to find
            
        Returns:
            True if expected value is found in resolved values
        """
        expected_lower = expected.lower().strip()
        
        for value in resolved_values:
            if expected_lower in value.lower():
                return True
        
        return False
