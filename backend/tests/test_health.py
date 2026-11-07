from backend.tests.helpers import make_test_client


def test_health_degraded_without_index(empty_catalog):
    with make_test_client(empty_catalog, service=None) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["rag_ready"] is False
    assert body["index"]["open"] is False
    assert body["catalog_verified"] is True
    assert body["catalog_programs"] == 0
    assert body["qdrant_local_workers"] == "single"
    assert "python_version" in body


def test_health_ok_when_service_injected(empty_catalog, mock_service):
    service, _ = mock_service
    with make_test_client(empty_catalog, service=service) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["rag_ready"] is True
    assert body["provider_mode"] == "mock"
