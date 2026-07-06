"""
Scripts Package

Utility scripts for setup and debugging.
Can be run standalone or imported for startup tasks.
"""

from scripts.setup_initial_org import (
    check_status,
    assign_user,
    create_superuser_if_not_exists,
)

__all__ = [
    "check_status",
    "assign_user", 
    "create_superuser_if_not_exists",
]
