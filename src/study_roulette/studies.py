import csv
import random
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class Study:
    url: str
    weight: float


class StudiesFileError(Exception):
    """Raised when the studies file is invalid."""

    pass


class StudyLineError(Exception):
    """Raised when a single line fails to parse."""

    pass


def parse_line(row: list[str]) -> Study:
    """Parse a row into a Study, raising StudyLineError on failure."""
    if len(row) != 2:
        raise StudyLineError(f"expected 2 columns, got {len(row)}")

    url_str, weight_str = row[0].strip(), row[1].strip()

    parsed = urlparse(url_str)
    if not parsed.scheme or not parsed.netloc:
        raise StudyLineError(f"invalid URL '{url_str}'")

    try:
        weight = float(weight_str)
    except ValueError:
        raise StudyLineError(f"invalid weight '{weight_str}'")

    if weight < 0:
        raise StudyLineError(f"weight must be non-negative, got {weight}")

    return Study(url=url_str, weight=weight)


def parse_studies_file(path: Path) -> list[Study]:
    """
    Parse a studies file and return a list of Study objects.

    The file is tab-delimited with columns: URL, weight
    Lines starting with # are comments. Empty lines are ignored.
    """
    try:
        file = path.open(newline="")
    except OSError as e:
        raise StudiesFileError(f"Cannot read studies file: {e}")

    errors: list[str] = []
    studies: list[Study] = []

    with file:
        reader = csv.reader(file, delimiter="\t")
        next(reader, None)  # skip header

        for line_num, row in enumerate(reader, start=2):
            if not row or row[0].startswith("#"):
                continue
            try:
                studies.append(parse_line(row))
            except StudyLineError as e:
                errors.append(f"Line {line_num}: {e}")

    if errors:
        raise StudiesFileError("Studies file errors:\n" + "\n".join(errors))

    if not studies:
        raise StudiesFileError("Studies file contains no valid entries")

    if all(s.weight == 0 for s in studies):
        raise StudiesFileError("At least one study must have a positive weight")

    return studies


def choose_study(studies: list[Study]) -> Study:
    """
    Choose a random study from the list using weighted selection.

    Studies with weight 0 are excluded from selection.
    """
    eligible = [s for s in studies if s.weight > 0]
    if not eligible:
        raise ValueError("No eligible studies with positive weight")

    weights = [s.weight for s in eligible]
    return random.choices(eligible, weights=weights, k=1)[0]
