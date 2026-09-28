"""Write-path load test. CREATES REAL ROWS IN YOUR DATABASE AND LEAVES THEM THERE.

Kept in a separate file from locustfile.py so that ordinary read-only runs can
never mutate data by accident.

    locust -f loadtest/write_locustfile.py --host http://localhost:5000

Every row is named with LOADTEST_PREFIX, so a run can be purged later with:
    DELETE FROM asset WHERE name LIKE 'loadtest-%';
"""

import os
import uuid

from dotenv import load_dotenv
from locust import HttpUser, between, task
from locust.exception import StopUser

load_dotenv()

EMAIL = os.getenv("FIRST_SUPERUSER", "")
PASSWORD = os.getenv("FIRST_SUPERUSER_PASSWORD", "")

LOADTEST_PREFIX = "loadtest-"
ASSET_TYPE = "Network Asset-Router"


class AssetWriteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
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

    @task
    def create_asset(self):
        payload = {
            "name": f"{LOADTEST_PREFIX}{uuid.uuid4().hex[:12]}",
            "asset_type": ASSET_TYPE,
            "description": "created by locust load test",
        }
        with self.client.post(
            "/api/assets/",
            json=payload,
            name="/api/assets/ [create]",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"create failed: {response.status_code} {response.text[:200]}")
