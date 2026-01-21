from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from study_roulette import build_app
from study_roulette.settings import Settings


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    lookup_dir = tmp_path / "lookups"
    lookup_dir.mkdir()
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text("URL\tweight\n" "https://example.com/survey?s=abc\t1\n")

    return Settings(lookup_dir=lookup_dir, studies_file=studies_file)


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    app = build_app(test_settings)
    return TestClient(app, follow_redirects=False)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["errors"] == []


def test_health_returns_error_for_missing_studies_file(tmp_path: Path) -> None:
    lookup_dir = tmp_path / "lookups"
    lookup_dir.mkdir()
    studies_file = tmp_path / "nonexistent.tsv"

    settings = Settings(lookup_dir=lookup_dir, studies_file=studies_file)
    app = build_app(settings)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert len(data["errors"]) > 0


def test_health_returns_error_for_invalid_studies_file(tmp_path: Path) -> None:
    lookup_dir = tmp_path / "lookups"
    lookup_dir.mkdir()
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text("URL\tweight\n")  # Empty, no valid entries

    settings = Settings(lookup_dir=lookup_dir, studies_file=studies_file)
    app = build_app(settings)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"


def test_sr_redirects(client: TestClient) -> None:
    response = client.get("/sr?email=foo@bar.com")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://example.com/survey")
    assert "s=abc" in location
    assert "email=foo%40bar.com" in location


def test_sr_redirect_is_stable(client: TestClient) -> None:
    req1 = client.get("/sr?email=foo@bar.com&ts=12345")
    for _ in range(100):
        req2 = client.get("/sr?email=foo@bar.com&ts=12345")
        assert req1.headers.get("location") == req2.headers.get("location")


def test_sr_different_params_can_differ(client: TestClient) -> None:
    response1 = client.get("/sr?email=a@b.com")
    response2 = client.get("/sr?email=x@y.com")

    # Locations differ because params differ
    assert response1.headers["location"] != response2.headers["location"]


def test_sr_handles_multi_value_params(client: TestClient) -> None:
    response = client.get("/sr?tag=a&tag=b")

    assert response.status_code == 302
    location = response.headers["location"]
    assert "tag=a" in location
    assert "tag=b" in location


def test_sr_with_no_params(client: TestClient) -> None:
    response = client.get("/sr")

    assert response.status_code == 302
