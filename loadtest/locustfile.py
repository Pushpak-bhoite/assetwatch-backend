"""Locust load test for the AssetWatch API.

Run:  locust -f loadtest/locustfile.py --host http://localhost:5000
Then open http://localhost:8089 and set users / spawn rate.

Credentials come from the environment (same names as .env):
    FIRST_SUPERUSER / FIRST_SUPERUSER_PASSWORD
"""

import os

from dotenv import load_dotenv
from locust import HttpUser, between, task
from locust.exception import StopUser

load_dotenv()

EMAIL = os.getenv("FIRST_SUPERUSER", "")
PASSWORD = os.getenv("FIRST_SUPERUSER_PASSWORD", "")


class AnonymousUser(HttpUser):
    """Hits only the endpoints that need no token."""

    weight = 1
    wait_time = between(1, 3)

    @task(3)
    def asset_types(self):
        self.client.get("/api/assets/types/list", name="/api/assets/types/list")

    @task(1)
    def beacon_health(self):
        self.client.get("/api/beacon/health", name="/api/beacon/health")


class AuthenticatedUser(HttpUser):
    """Logs in once, then loops over the read-heavy dashboard endpoints."""

    weight = 4
    wait_time = between(1, 3)

    def on_start(self):
        """Called once per simulated user when it starts."""
        with self.client.post(
            "/api/auth/jwt/login",
            data={"username": EMAIL, "password": PASSWORD},
            name="/api/auth/jwt/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login failed: {response.status_code} {response.text[:200]}")
                raise StopUser
            token = response.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(5)
    def dashboard_overview(self):
        self.client.get("/api/dashboard/overview", name="/api/dashboard/overview")

    @task(4)
    def list_assets(self):
        self.client.get("/api/assets/?page=1&limit=10", name="/api/assets/ [paginated]")

    @task(3)
    def list_monitors(self):
        self.client.get("/api/monitors?page=1&limit=10", name="/api/monitors [paginated]")

    @task(2)
    def monitor_stats(self):
        self.client.get("/api/monitors/stats", name="/api/monitors/stats")

    @task(2)
    def observability_assets(self):
        self.client.get(
            "/api/observability/assets?page=1&limit=10",
            name="/api/observability/assets [paginated]",
        )
    @task(1)
    def me(self):
        self.client.get("/api/users/me", name="/api/users/me")

    @task(1)
    def full_dashboard(self):
        # Heaviest endpoint: aggregates overview + activity + trend + warnings.
        self.client.get("/api/dashboard?trend_range=24h", name="/api/dashboard")
