from pathlib import Path

from study_roulette.redirect import compute_hash, merge_urls, get_or_create_redirect


def test_compute_hash_is_stable() -> None:
    params = {"email": ["foo@bar.com"], "ts": ["12345"]}

    hash1 = compute_hash(params)
    hash2 = compute_hash(params)

    assert hash1 == hash2


def test_compute_hash_is_order_independent() -> None:
    params1 = {"email": ["foo@bar.com"], "ts": ["12345"]}
    params2 = {"ts": ["12345"], "email": ["foo@bar.com"]}

    assert compute_hash(params1) == compute_hash(params2)


def test_compute_hash_sorts_values() -> None:
    params1 = {"tags": ["a", "b", "c"]}
    params2 = {"tags": ["c", "b", "a"]}

    assert compute_hash(params1) == compute_hash(params2)


def test_compute_hash_differs_for_different_params() -> None:
    params1 = {"email": ["foo@bar.com"]}
    params2 = {"email": ["other@bar.com"]}

    assert compute_hash(params1) != compute_hash(params2)


def test_merge_urls_adds_params_to_base() -> None:
    base_url = "https://example.com/survey"
    incoming = {"email": ["foo@bar.com"], "ts": ["12345"]}

    result = merge_urls(base_url, incoming)

    assert "email=foo%40bar.com" in result
    assert "ts=12345" in result


def test_merge_urls_base_params_take_precedence() -> None:
    base_url = "https://example.com/survey?study_id=abc"
    incoming = {"study_id": ["xyz"], "email": ["foo@bar.com"]}

    result = merge_urls(base_url, incoming)

    assert "study_id=abc" in result
    assert "study_id=xyz" not in result
    assert "email=foo%40bar.com" in result


def test_merge_urls_preserves_base_url_structure() -> None:
    base_url = "https://example.com/path/to/survey?s=12345"
    incoming = {"email": ["foo@bar.com"]}

    result = merge_urls(base_url, incoming)

    assert result.startswith("https://example.com/path/to/survey")
    assert "s=12345" in result


def test_get_or_create_redirect_creates_new(tmp_path: Path) -> None:
    lookup_dir = tmp_path / "lookups"
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/survey?s=abc\t1\n"
    )
    params = {"email": ["foo@bar.com"]}

    result = get_or_create_redirect(lookup_dir, studies_file, params)

    assert result.startswith("https://example.com/survey")
    assert "s=abc" in result
    assert "email=foo%40bar.com" in result


def test_get_or_create_redirect_returns_cached(tmp_path: Path) -> None:
    lookup_dir = tmp_path / "lookups"
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/survey1\t1\n"
        "https://example.com/survey2\t1\n"
    )
    params = {"email": ["foo@bar.com"]}

    result1 = get_or_create_redirect(lookup_dir, studies_file, params)
    result2 = get_or_create_redirect(lookup_dir, studies_file, params)

    assert result1 == result2


def test_get_or_create_redirect_different_params_different_results(tmp_path: Path) -> None:
    lookup_dir = tmp_path / "lookups"
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/survey\t1\n"
    )

    result1 = get_or_create_redirect(lookup_dir, studies_file, {"email": ["a@b.com"]})
    result2 = get_or_create_redirect(lookup_dir, studies_file, {"email": ["x@y.com"]})

    # URLs will be different due to different email params
    assert result1 != result2


def test_get_or_create_redirect_creates_lookup_dir(tmp_path: Path) -> None:
    lookup_dir = tmp_path / "nested" / "lookups"
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/survey\t1\n"
    )

    get_or_create_redirect(lookup_dir, studies_file, {"email": ["foo@bar.com"]})

    assert lookup_dir.exists()
