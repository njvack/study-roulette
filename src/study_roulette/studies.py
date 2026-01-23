import logging
import random
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class Study:
    url: str
    weight: float
    note: str | None = None


@dataclass
class ParseResult:
    studies: list["Study"]
    errors: list[str]


class StudiesFileError(Exception):
    """Raised when the studies file cannot be read at all."""

    pass


def parse_study_entry(entry: Any, index: int) -> Study:
    """Parse a single study entry from TOML, raising StudiesFileError on failure."""
    if not isinstance(entry, dict):
        raise StudiesFileError(f"studies[{index}]: expected a table, got {type(entry).__name__}")

    if "url" not in entry:
        raise StudiesFileError(f"studies[{index}]: missing required key 'url'")
    if "weight" not in entry:
        raise StudiesFileError(f"studies[{index}]: missing required key 'weight'")

    url_str = entry["url"]
    if not isinstance(url_str, str):
        raise StudiesFileError(f"studies[{index}]: 'url' must be a string")

    parsed = urlparse(url_str)
    if not parsed.scheme or not parsed.netloc:
        raise StudiesFileError(f"studies[{index}]: invalid URL '{url_str}'")

    weight = entry["weight"]
    if not isinstance(weight, (int, float)):
        raise StudiesFileError(f"studies[{index}]: 'weight' must be a number")

    if weight < 0:
        raise StudiesFileError(f"studies[{index}]: weight must be non-negative, got {weight}")

    note = entry.get("note")
    if note is not None:
        note = str(note)

    return Study(url=url_str, weight=float(weight), note=note)


def parse_studies_file(path: Path) -> ParseResult:
    """
    Parse a TOML studies file and return valid studies and any errors.

    Expected format:
        studies = [
            {url = "https://example.com/study1", weight = 1},
            {url = "https://example.com/study2", weight = 2},
        ]

    Fatal errors (can't read file, invalid TOML, missing studies key) raise StudiesFileError.
    Individual study parsing errors are returned in ParseResult.errors alongside valid studies.
    """
    logger.debug("Parsing studies file: %s", path)
    try:
        content = path.read_bytes()
    except OSError as e:
        raise StudiesFileError(f"Cannot read studies file: {e}")

    try:
        data = tomllib.loads(content.decode("utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise StudiesFileError(f"Invalid TOML: {e}")

    if "studies" not in data:
        raise StudiesFileError("Missing required key 'studies'")

    studies_data = data["studies"]
    if not isinstance(studies_data, list):
        raise StudiesFileError("'studies' must be an array")

    studies: list[Study] = []
    errors: list[str] = []

    for i, entry in enumerate(studies_data):
        try:
            studies.append(parse_study_entry(entry, i))
        except StudiesFileError as e:
            errors.append(str(e))

    if not studies:
        errors.append("No valid studies found")

    if studies and all(s.weight == 0 for s in studies):
        errors.append("At least one study must have a positive weight")

    logger.debug("Loaded %d studies from %s", len(studies), path.name)
    return ParseResult(studies=studies, errors=errors)


def choose_study(studies: list[Study]) -> Study:
    """
    Choose a random study from the list using weighted selection.

    Studies with weight 0 are excluded from selection.
    """
    eligible = [s for s in studies if s.weight > 0]
    if not eligible:
        raise ValueError("No eligible studies with positive weight")

    weights = [s.weight for s in eligible]
    chosen = random.choices(eligible, weights=weights, k=1)[0]
    logger.debug(
        "Selected study %s (weight %.2f) from %d eligible studies",
        chosen.url,
        chosen.weight,
        len(eligible),
    )
    return chosen
