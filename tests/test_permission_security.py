import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_unauthenticated_requests_fail(client: TestClient):
    # GET /issues/ without authentication token should fail (401 or 403)
    response = client.get("/issues/")
    assert response.status_code in (401, 403)

    # GET /receipts/ without auth
    response = client.get("/receipts/")
    assert response.status_code in (401, 403)

    # GET /returns/ without auth
    response = client.get("/returns/")
    assert response.status_code in (401, 403)

    # GET /transfers/ without auth
    response = client.get("/transfers/")
    assert response.status_code in (401, 403)

    # GET /outward-passes/ without auth
    response = client.get("/outward-passes/")
    assert response.status_code in (401, 403)

    # GET /stock/balance without auth
    response = client.get("/stock/balance")
    assert response.status_code in (401, 403)
