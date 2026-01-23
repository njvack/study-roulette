import logging
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")

    lookup_dir: Path
    studies_file: Path
    log_level: LogLevel = "INFO"

    def configure_logging(self) -> None:
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
