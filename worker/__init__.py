"""
AssetWatch Monitoring Worker

A standalone worker process that executes scheduled monitoring checks.
Uses APScheduler to periodically check monitors and update their status.

Usage:
    python -m worker.main

Architecture:
    - scheduler.py: APScheduler configuration
    - engine.py: Main check orchestration
    - checkers/: Protocol-specific check implementations
"""

__version__ = "1.0.0"
