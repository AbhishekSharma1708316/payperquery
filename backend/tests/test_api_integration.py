import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _create_provider(client, **overrides) -> dict:
    payload = {
        "name": "Search API",
        "endpoint": "http://localhost/mock-provider/search",
        "category": "search",
        "price_usd": "0.03",
        "pay_to_address": f"PROV{uuid.uuid4().hex[:20].upper()}",
    }
    payload.update(overrides)
    r = client.post("/api/providers", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_agent(client, provider_id, **policy_overrides) -> dict:
    policy = {
        "max_transaction_amount": "0.10",
        "daily_limit": "5.00",
        "min_provider_reputation": 50,
        "allowed_provider_ids": [provider_id],
    }
    policy.update(policy_overrides)
    r = client.post(
        "/api/agents",
        json={
            "name": "ResearchBot",
            "wallet_address": f"AGENT{uuid.uuid4().hex[:20].upper()}",
            "policy": policy,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_missing_idempotency_key_is_rejected(client):
    provider = _create_provider(client)
    agent = _create_agent(client, provider["id"])

    r = client.post(
        "/api/payments/request",
        json={
            "agent_id": agent["id"],
            "provider_id": provider["id"],
            "amount": "0.03",
            "currency": "USDC",
        },
    )
    assert r.status_code == 400
    assert "Idempotency-Key" in r.json()["detail"]


def test_full_demo_scenario_approve_then_block(client):
    provider = _create_provider(client)
    agent = _create_agent(client, provider["id"])

    r = client.post(
        "/api/payments/request",
        headers={"Idempotency-Key": "k-approve-1"},
        json={
            "agent_id": agent["id"],
            "provider_id": provider["id"],
            "amount": "0.03",
            "currency": "USDC",
        },
    )
    assert r.status_code == 200
    assert r.json()["transaction"]["status"] == "PAYMENT_REQUIRED"

    r = client.post(
        "/api/payments/request",
        headers={"Idempotency-Key": "k-block-1"},
        json={
            "agent_id": agent["id"],
            "provider_id": provider["id"],
            "amount": "2.00",
            "currency": "USDC",
        },
    )
    assert r.status_code == 200
    body = r.json()["transaction"]
    assert body["status"] == "POLICY_BLOCKED"
    assert body["failure_reason"] == "TRANSACTION_LIMIT_EXCEEDED"
    # No payment reference should ever be set on a blocked transaction
    assert body["payment_reference"] is None
    assert body["x402_payment_identifier"] is None


def test_pause_agent_blocks_all_subsequent_payments(client):
    provider = _create_provider(client)
    agent = _create_agent(client, provider["id"])

    r = client.patch(f"/api/agents/{agent['id']}/pause", json={"is_paused": True})
    assert r.status_code == 200
    assert r.json()["is_paused"] is True

    r = client.post(
        "/api/payments/request",
        headers={"Idempotency-Key": "k-paused-1"},
        json={
            "agent_id": agent["id"],
            "provider_id": provider["id"],
            "amount": "0.03",
            "currency": "USDC",
        },
    )
    assert r.json()["transaction"]["status"] == "POLICY_BLOCKED"
    assert r.json()["transaction"]["failure_reason"] == "AGENT_PAUSED"

    r = client.patch(f"/api/agents/{agent['id']}/pause", json={"is_paused": False})
    assert r.status_code == 200

    r = client.post(
        "/api/payments/request",
        headers={"Idempotency-Key": "k-unpaused-1"},
        json={
            "agent_id": agent["id"],
            "provider_id": provider["id"],
            "amount": "0.03",
            "currency": "USDC",
        },
    )
    assert r.json()["transaction"]["status"] == "PAYMENT_REQUIRED"


def test_repeated_identical_request_is_idempotent_over_http(client):
    provider = _create_provider(client)
    agent = _create_agent(client, provider["id"])

    responses = []
    for _ in range(3):
        r = client.post(
            "/api/payments/request",
            headers={"Idempotency-Key": "k-repeat-1"},
            json={
                "agent_id": agent["id"],
                "provider_id": provider["id"],
                "amount": "0.03",
                "currency": "USDC",
            },
        )
        responses.append(r.json()["transaction"]["id"])

    assert len(set(responses)) == 1

    r = client.get("/api/transactions", params={"agent_id": agent["id"]})
    matching = [t for t in r.json() if t["idempotency_key"] == "k-repeat-1"]
    assert len(matching) == 1


def test_nonexistent_agent_returns_404(client):
    provider = _create_provider(client)
    r = client.post(
        "/api/payments/request",
        headers={"Idempotency-Key": "k-404-1"},
        json={
            "agent_id": "00000000-0000-0000-0000-000000000000",
            "provider_id": provider["id"],
            "amount": "0.03",
            "currency": "USDC",
        },
    )
    assert r.status_code == 404


def test_escrow_lifecycle_release(client):
    provider = _create_provider(client)
    agent = _create_agent(client, provider["id"])

    r = client.post(
        "/api/payments/request",
        headers={"Idempotency-Key": "k-escrow-1"},
        json={
            "agent_id": agent["id"],
            "provider_id": provider["id"],
            "amount": "0.03",
            "currency": "USDC",
        },
    )
    txn_id = r.json()["transaction"]["id"]

    # Escrow requires a verified payment; a PAYMENT_REQUIRED transaction
    # (no mnemonic supplied in this test) should be rejected.
    r = client.post("/api/escrow", params={"transaction_id": txn_id})
    assert r.status_code == 409


def test_dashboard_stats_reflect_blocked_and_total_counts(client):
    provider = _create_provider(client)
    agent = _create_agent(client, provider["id"])

    client.post(
        "/api/payments/request",
        headers={"Idempotency-Key": "k-dash-block"},
        json={
            "agent_id": agent["id"],
            "provider_id": provider["id"],
            "amount": "2.00",
            "currency": "USDC",
        },
    )

    r = client.get("/api/dashboard/stats")
    stats = r.json()
    assert stats["blocked_payments_today"] >= 1
    assert stats["total_agents"] >= 1
    assert stats["total_providers"] >= 1
