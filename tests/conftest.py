from collections.abc import Callable
from pathlib import Path

import pytest

from study_roulette.settings import Settings
from study_roulette.studies import Study


@pytest.fixture
def make_settings(tmp_path: Path) -> Callable[[list[Study]], Settings]:
    """
    Factory fixture that creates Settings with a studies file.

    Usage:
        def test_something(make_settings):
            settings = make_settings([
                Study(url="https://example.com/a", weight=1),
                Study(url="https://example.com/b", weight=2),
            ])
    """

    def _make_settings(studies: list[Study]) -> Settings:
        lookup_dir = tmp_path / "lookups"
        lookup_dir.mkdir(exist_ok=True)

        studies_file = tmp_path / "studies.toml"

        lines = []
        for s in studies:
            parts = [f'url = "{s.url}"', f"weight = {s.weight}"]
            if s.note is not None:
                parts.append(f'note = "{s.note}"')
            lines.append("    {" + ", ".join(parts) + "}")

        content = "studies = [\n" + ",\n".join(lines) + ",\n]"
        studies_file.write_text(content)

        return Settings(lookup_dir=lookup_dir, studies_file=studies_file)

    return _make_settings
