from backend.tests.helpers import make_test_client


def test_programs_empty_verified_catalog(empty_catalog):
    with make_test_client(empty_catalog) as client:
        response = client.get("/api/programs")
    assert response.status_code == 200
    assert response.json() == []


def test_programs_lists_verified_entries_only(populated_catalog):
    with make_test_client(populated_catalog) as client:
        response = client.get("/api/programs")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["program_id"] == "eng"
    assert body[0]["name"] == "Engineering Fixture"
    assert set(body[0]["plan_versions"]) == {"2024", "2025"}
    assert "document_ids" not in body[0]
