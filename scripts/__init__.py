"""
Scripts package for AssetWatch backend.

Contains utility scripts that can be run standalone or imported.
"""

from scripts.setup_initial_org import create_superuser_if_not_exists

__all__ = ["create_superuser_if_not_exists"]
