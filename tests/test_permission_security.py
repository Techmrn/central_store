import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_unauthenticated_requests_fail(client: TestClient):
    # GET /issues/ without authentication token should fail (401, 403, or 303 redirect)
    response = client.get("/issues/", follow_redirects=False)
    assert response.status_code in (401, 403, 303)

    # GET /receipts/ without auth
    response = client.get("/receipts/", follow_redirects=False)
    assert response.status_code in (401, 403, 303)

    # GET /returns/ without auth
    response = client.get("/returns/", follow_redirects=False)
    assert response.status_code in (401, 403, 303)

    # GET /transfers/ without auth
    response = client.get("/transfers/", follow_redirects=False)
    assert response.status_code in (401, 403, 303)

    # GET /outward-passes/ without auth
    response = client.get("/outward-passes/", follow_redirects=False)
    assert response.status_code in (401, 403, 303)

    # GET /stock/balance without auth
    response = client.get("/stock/balance", follow_redirects=False)
    assert response.status_code in (401, 403, 303)
