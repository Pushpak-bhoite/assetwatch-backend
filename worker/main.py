"""
Worker Entry Point

Starts the APScheduler and runs the monitoring worker process.
This should be run as a separate process from the FastAPI application.

Usage:
    python -m worker.main
    
    # Or with poetry/uv:
    uv run python -m worker.main
"""

import asyncio
import signal
import sys
from datetime import datetime

from worker.scheduler import create_scheduler, start_scheduler, shutdown_scheduler


async def main():
    """Main entry point for the monitoring worker."""
    print(f"[{datetime.now().isoformat()}] Starting AssetWatch Monitoring Worker...")
    
    # Create and start the scheduler
    scheduler = create_scheduler()
    
    # Handle graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        print(f"\n[{datetime.now().isoformat()}] Received shutdown signal ({sig})")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start scheduler
        start_scheduler(scheduler)
        print(f"[{datetime.now().isoformat()}] Worker started. Press Ctrl+C to stop.")
        
        # Keep running until shutdown signal
        await shutdown_event.wait()
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Error: {e}")
        raise
    finally:
        # Graceful shutdown
        print(f"[{datetime.now().isoformat()}] Shutting down worker...")
        shutdown_scheduler(scheduler)
        print(f"[{datetime.now().isoformat()}] Worker stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker interrupted.")
        sys.exit(0)
