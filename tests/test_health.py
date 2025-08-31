import os

from fastapi.testclient import TestClient

# Disable OTEL for local unit tests
os.environ.setdefault("OTEL_DISABLED", "1")
os.environ.setdefault("KAFKA_DISABLED", "1")


def _check(app):
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_orders_health():
    from services.orders.app.main import app as orders_app

    _check(orders_app)


def test_payments_health():
    from services.payments.app.main import app as payments_app

    _check(payments_app)


def test_inventory_health():
    from services.inventory.app.main import app as inventory_app

    _check(inventory_app)


def test_orchestrator_health():
    from services.orchestrator.app.main import app as orchestrator_app

    _check(orchestrator_app)
