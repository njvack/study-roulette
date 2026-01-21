import pytest
from pathlib import Path

from study_roulette.studies import Study, StudiesFileError, parse_studies_file, choose_study


def test_parses_valid_file(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\t1\n"
        "https://example.com/study2\t2\n"
    )

    studies = parse_studies_file(studies_file)

    assert len(studies) == 2
    assert studies[0] == Study(url="https://example.com/study1", weight=1.0)
    assert studies[1] == Study(url="https://example.com/study2", weight=2.0)


def test_handles_crlf_line_endings(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\r\n"
        "https://example.com/study1\t1\r\n"
        "https://example.com/study2\t2\r\n"
    )

    studies = parse_studies_file(studies_file)

    assert len(studies) == 2


def test_handles_mixed_line_endings(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\t1\r\n"
        "https://example.com/study2\t2\n"
    )

    studies = parse_studies_file(studies_file)

    assert len(studies) == 2


def test_ignores_comments(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "# This is a comment\n"
        "https://example.com/study1\t1\n"
        "# Another comment\n"
        "https://example.com/study2\t2\n"
    )

    studies = parse_studies_file(studies_file)

    assert len(studies) == 2


def test_ignores_empty_lines(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "\n"
        "https://example.com/study1\t1\n"
        "\n"
        "https://example.com/study2\t2\n"
        "\n"
    )

    studies = parse_studies_file(studies_file)

    assert len(studies) == 2


def test_strips_whitespace_from_urls(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "  https://example.com/study1  \t1\n"
    )

    studies = parse_studies_file(studies_file)

    assert studies[0].url == "https://example.com/study1"


def test_accepts_zero_weight(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\t0\n"
        "https://example.com/study2\t1\n"
    )

    studies = parse_studies_file(studies_file)

    assert len(studies) == 2
    assert studies[0].weight == 0.0


def test_accepts_decimal_weights(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\t0.5\n"
        "https://example.com/study2\t1.5\n"
    )

    studies = parse_studies_file(studies_file)

    assert studies[0].weight == 0.5
    assert studies[1].weight == 1.5


def test_raises_on_missing_file(tmp_path: Path) -> None:
    studies_file = tmp_path / "nonexistent.tsv"

    with pytest.raises(StudiesFileError, match="Cannot read studies file"):
        parse_studies_file(studies_file)


def test_raises_on_empty_file(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text("URL\tweight\n")

    with pytest.raises(StudiesFileError, match="no valid entries"):
        parse_studies_file(studies_file)


def test_raises_on_invalid_url(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "not-a-url\t1\n"
    )

    with pytest.raises(StudiesFileError, match="invalid URL"):
        parse_studies_file(studies_file)


def test_raises_on_negative_weight(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\t-1\n"
    )

    with pytest.raises(StudiesFileError, match="non-negative"):
        parse_studies_file(studies_file)


def test_raises_on_invalid_weight(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\tabc\n"
    )

    with pytest.raises(StudiesFileError, match="invalid weight"):
        parse_studies_file(studies_file)


def test_raises_on_all_zero_weights(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\t0\n"
        "https://example.com/study2\t0\n"
    )

    with pytest.raises(StudiesFileError, match="positive weight"):
        parse_studies_file(studies_file)


def test_raises_on_wrong_column_count(tmp_path: Path) -> None:
    studies_file = tmp_path / "studies.tsv"
    studies_file.write_text(
        "URL\tweight\n"
        "https://example.com/study1\n"
    )

    with pytest.raises(StudiesFileError, match="expected 2 columns"):
        parse_studies_file(studies_file)


def test_choose_study_chooses_from_studies() -> None:
    studies = [
        Study(url="https://example.com/study1", weight=1.0),
        Study(url="https://example.com/study2", weight=1.0),
    ]

    chosen = choose_study(studies)

    assert chosen in studies


def test_choose_study_excludes_zero_weight() -> None:
    studies = [
        Study(url="https://example.com/study1", weight=0.0),
        Study(url="https://example.com/study2", weight=1.0),
    ]

    for _ in range(100):
        chosen = choose_study(studies)
        assert chosen.url == "https://example.com/study2"


def test_choose_study_respects_weights() -> None:
    studies = [
        Study(url="https://example.com/study1", weight=1.0),
        Study(url="https://example.com/study2", weight=99.0),
    ]

    counts = {"study1": 0, "study2": 0}
    for _ in range(1000):
        chosen = choose_study(studies)
        if "study1" in chosen.url:
            counts["study1"] += 1
        else:
            counts["study2"] += 1

    # study2 should be chosen roughly 99x more often
    assert counts["study2"] > counts["study1"] * 10


def test_choose_study_raises_on_no_eligible() -> None:
    studies = [
        Study(url="https://example.com/study1", weight=0.0),
    ]

    with pytest.raises(ValueError, match="No eligible studies"):
        choose_study(studies)
