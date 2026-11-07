from backend.tests.helpers import make_test_client


def test_chat_rejects_extra_fields(empty_catalog, mock_service):
    service, _ = mock_service
    with make_test_client(empty_catalog, service=service) as client:
        response = client.post(
            "/api/chat",
            json={
                "question": "How long are loans?",
                "language": "en",
                "api_key": "secret",
            },
        )
    assert response.status_code == 422


def test_chat_rejects_overlong_question(empty_catalog, mock_service):
    service, _ = mock_service
    with make_test_client(empty_catalog, service=service) as client:
        response = client.post(
            "/api/chat",
            json={"question": "x" * 2001, "language": "en"},
        )
    assert response.status_code == 422


def test_chat_rejects_invalid_language(empty_catalog, mock_service):
    service, _ = mock_service
    with make_test_client(empty_catalog, service=service) as client:
        response = client.post(
            "/api/chat",
            json={"question": "How long are loans?", "language": "fr"},
        )
    assert response.status_code == 422


def test_chat_requires_program_and_plan_together(populated_catalog, mock_service):
    service, _ = mock_service
    with make_test_client(populated_catalog, service=service) as client:
        response = client.post(
            "/api/chat",
            json={"question": "How long are loans?", "language": "en", "program_id": "eng"},
        )
    assert response.status_code == 422


def test_chat_rejects_unknown_program(populated_catalog, mock_service):
    service, _ = mock_service
    with make_test_client(populated_catalog, service=service) as client:
        response = client.post(
            "/api/chat",
            json={
                "question": "How long are loans?",
                "language": "en",
                "program_id": "missing",
                "plan_version": "2024",
            },
        )
    assert response.status_code == 422


def test_chat_503_when_rag_not_ready(empty_catalog):
    with make_test_client(empty_catalog, service=None) as client:
        response = client.post(
            "/api/chat",
            json={"question": "How long are loans?", "language": "en"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "rag_not_ready"


def test_chat_returns_rag_response_contract(empty_catalog, mock_service):
    service, _ = mock_service
    with make_test_client(empty_catalog, service=service) as client:
        response = client.post(
            "/api/chat",
            json={"question": "How long are loans?", "language": "en"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "1.0.0"
    assert body["status"] == "answered"
    assert body["mode"] == "mock"
    assert body["language"] == "en"
    assert isinstance(body["sources"], list)
    assert isinstance(body["claims"], list)
    assert "latency" in body and "validation" in body
