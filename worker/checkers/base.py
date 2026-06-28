"""
Base Checker Classes and Types

Defines the CheckResult dataclass and base checker interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.db import StandaloneMonitor


@dataclass
class CheckResult:
    """
    Result of a monitor check.
    
    Attributes:
        success: Whether the check passed
        response_time: Time taken for the check in milliseconds
        error_message: Error description if check failed (optional)
        resolved_value: For DNS checks, the resolved value (optional)
        status_code: For HTTP checks, the HTTP status code (optional)
    """
    success: bool
    response_time: float  # milliseconds
    error_message: Optional[str] = None
    resolved_value: Optional[str] = None
    status_code: Optional[int] = None


class BaseChecker(ABC):
    """
    Abstract base class for all checkers.
    
    Each checker must implement the `check()` method which performs
    the actual monitoring check and returns a CheckResult.
    """
    
    @abstractmethod
    async def check(self, monitor: "StandaloneMonitor") -> CheckResult:
        """
        Perform a monitoring check.
        
        Args:
            monitor: The StandaloneMonitor to check
            
        Returns:
            CheckResult with success status and details
        """
        pass
