from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from study_roulette import build_app
from study_roulette.app import StudyRoulette
from study_roulette.settings import Settings
from study_roulette.studies import Study


@pytest.fixture
def client(make_settings: Callable[[list[Study]], Settings]) -> TestClient:
    settings = make_settings([Study(url="https://example.com/survey?s=abc", weight=1)])
    app = build_app(settings)
    return TestClient(app, follow_redirects=False)


def test_study_roulette_from_settings(
    make_settings: Callable[[list[Study]], Settings],
) -> None:
    studies = [Study(url="https://example.com/survey?s=abc", weight=1)]
    settings = make_settings(studies)

    sr = StudyRoulette.from_settings(settings)
    assert len(sr.studies) == len(studies)


def test_study_roulette_excludes_bad_studies(
    make_settings: Callable[[list[Study]], Settings],
) -> None:
    studies = [
        Study(url="https://example.com/survey?s=abc", weight=1),
        Study(url="https://example.com/survey?s=abc", weight=0),
        Study(url="not-a-url", weight=1),
    ]
    settings = make_settings(studies)
    sr = StudyRoulette.from_settings(settings)

    assert len(sr.studies) == 2
    assert len(sr.errors) > 0


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["errors"] == []
    assert data["studies"] == [
        {"url": "https://example.com/survey?s=abc", "weight": 1.0, "percent": 100.0}
    ]


def test_health_returns_error_for_missing_studies_file(tmp_path: Path) -> None:
    lookup_dir = tmp_path / "lookups"
    lookup_dir.mkdir()
    studies_file = tmp_path / "nonexistent.toml"

    settings = Settings(lookup_dir=lookup_dir, studies_file=studies_file)
    app = build_app(settings)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert len(data["errors"]) > 0
    assert data["studies"] == []


def test_health_returns_error_for_invalid_studies_file(
    make_settings: Callable[[list[Study]], Settings],
) -> None:
    settings = make_settings([])  # No studies!
    app = build_app(settings)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"


def test_sr_redirects(client: TestClient) -> None:
    response = client.get("/?email=foo@bar.com")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://example.com/survey")
    assert "s=abc" in location
    assert "email=foo%40bar.com" in location


def test_sr_redirect_is_stable(client: TestClient) -> None:
    req1 = client.get("/?email=foo@bar.com&ts=12345")
    for _ in range(100):
        req2 = client.get("/?email=foo@bar.com&ts=12345")
        assert req1.headers.get("location") == req2.headers.get("location")


def test_sr_different_params_can_differ(client: TestClient) -> None:
    response1 = client.get("/?email=a@b.com")
    response2 = client.get("/?email=x@y.com")

    # Locations differ because params differ
    assert response1.headers["location"] != response2.headers["location"]


def test_sr_handles_multi_value_params(client: TestClient) -> None:
    response = client.get("/?tag=a&tag=b")

    assert response.status_code == 302
    location = response.headers["location"]
    assert "tag=a" in location
    assert "tag=b" in location


def test_sr_with_no_params(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 404


def test_health_shows_percent(
    make_settings: Callable[[list[Study]], Settings],
) -> None:
    settings = make_settings(
        [
            Study(url="https://example.com/a", weight=1),
            Study(url="https://example.com/b", weight=2),
            Study(url="https://example.com/c", weight=1),
        ]
    )
    app = build_app(settings)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert data["studies"][0]["percent"] == 25.0
    assert data["studies"][1]["percent"] == 50.0
    assert data["studies"][2]["percent"] == 25.0


def test_sr_distribution_matches_weights(
    make_settings: Callable[[list[Study]], Settings],
) -> None:
    settings = make_settings(
        [
            Study(url="https://example.com/a", weight=1),
            Study(url="https://example.com/b", weight=2),
        ]
    )
    app = build_app(settings)
    client = TestClient(app, follow_redirects=False)

    counts = {"a": 0, "b": 0}
    for i in range(300):
        response = client.get(f"/?id={i}")
        location = response.headers["location"]
        if "/a?" in location:
            counts["a"] += 1
        else:
            counts["b"] += 1

    # With weights 1:2, we expect roughly 100:200 distribution
    # Allow for randomness but b should be clearly more frequent
    assert counts["b"] > counts["a"], f"Expected b > a, got {counts}"
    # b should be roughly 2x a (within reasonable bounds for 300 samples)
    ratio = counts["b"] / counts["a"]
    assert 1.3 < ratio < 3.0, f"Expected ratio ~2, got {ratio:.2f} ({counts})"


def test_health_includes_notes(
    make_settings: Callable[[list[Study]], Settings],
) -> None:
    settings = make_settings(
        [
            Study(url="https://example.com/a", weight=1, note="Study A"),
            Study(url="https://example.com/b", weight=1),
        ]
    )
    app = build_app(settings)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert data["studies"][0]["note"] == "Study A"
    assert "note" not in data["studies"][1]  # excluded when None


def test_health_returns_errors_and_valid_studies(tmp_path: Path) -> None:
    """When some studies fail to parse, health returns both errors AND valid studies."""
    lookup_dir = tmp_path / "lookups"
    lookup_dir.mkdir()
    studies_file = tmp_path / "studies.toml"
    studies_file.write_text(
        """
studies = [
    {url = "https://example.com/valid", weight = 1},
    {url = "not-a-url", weight = 1},
]
"""
    )

    settings = Settings(lookup_dir=lookup_dir, studies_file=studies_file)
    app = build_app(settings)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert len(data["errors"]) > 0
    assert len(data["studies"]) == 1
    assert data["studies"][0]["url"] == "https://example.com/valid"


def test_sr_redirects_despite_parse_errors(tmp_path: Path) -> None:
    """Redirects still work when there are parse errors but valid studies."""
    lookup_dir = tmp_path / "lookups"
    lookup_dir.mkdir()
    studies_file = tmp_path / "studies.toml"
    studies_file.write_text(
        """
studies = [
    {url = "https://example.com/valid", weight = 1},
    {url = "not-a-url", weight = 1},
]
"""
    )

    settings = Settings(lookup_dir=lookup_dir, studies_file=studies_file)
    app = build_app(settings)
    client = TestClient(app, follow_redirects=False)

    response = client.get("/?id=123")

    assert response.status_code == 302
    assert "example.com/valid" in response.headers["location"]
