"""Live-HTTP integration tests against a real running hotel_erp site.

These deliberately do NOT use `bench run-tests`/FrappeTestCase: the two
things most worth proving here (NFR-A2 concurrency under real MariaDB lock
contention, and the bearer-auth service-user permission boundary) only mean
something over a real HTTP+DB round trip, matching this project's own
established verification standard ("real, not synthetic" -- see every
ROADMAP.md in this repo). A FrappeTestCase calling the whitelisted function
directly in-process wouldn't exercise either.

Configured entirely via environment variables so the same suite runs
against a local dev stack or a freshly bootstrapped CI site:

  ERP_BASE_URL          e.g. http://localhost:8001 (erp-nginx) or
                        http://localhost:8000 (erp-backend directly, no nginx)
  ERP_HOST_HEADER       e.g. hotel-beta.localhost -- selects the site
  ERP_BEARER_TOKEN      Sync Config's aggregator_api_key for that site
  ERP_ROOM_TYPE_CODE    a Room Type `code` with a Rate Plan + Rate Calendar
                        rows far enough in the future to be safe to hammer
  ERP_RATE_PLAN_CODE
  ERP_ROOMS_PER_NIGHT   rooms_available on the test nights (must be known
                        exactly -- the concurrency test asserts against it)
"""
from __future__ import annotations

import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("ERP_BASE_URL", "http://localhost:8001")
HOST_HEADER = os.environ.get("ERP_HOST_HEADER", "hotel-beta.localhost")
BEARER_TOKEN = os.environ.get("ERP_BEARER_TOKEN", "")
ROOM_TYPE_CODE = os.environ.get("ERP_ROOM_TYPE_CODE", "DLX-SEA")
RATE_PLAN_CODE = os.environ.get("ERP_RATE_PLAN_CODE", "FLEX")
ROOMS_PER_NIGHT = int(os.environ.get("ERP_ROOMS_PER_NIGHT", "3"))


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def room_type_code() -> str:
    return ROOM_TYPE_CODE


@pytest.fixture(scope="session")
def rate_plan_code() -> str:
    return RATE_PLAN_CODE


@pytest.fixture(scope="session")
def rooms_per_night() -> int:
    return ROOMS_PER_NIGHT


@pytest.fixture(scope="session")
def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Host": HOST_HEADER,
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json",
    })
    return s


def _api_url(path: str) -> str:
    return f"{BASE_URL}/api/v1{path}"


@pytest.fixture(scope="session")
def api_url():
    return _api_url


@pytest.fixture
def new_idempotency_key():
    return lambda: str(uuid.uuid4())
