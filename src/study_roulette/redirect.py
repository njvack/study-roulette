import fcntl
import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .studies import Study, choose_study, parse_studies_file

logger = logging.getLogger(__name__)


def compute_hash(params: dict[str, list[str]]) -> str:
    """
    Compute a stable SHA256 hash from URL parameters.

    Parameters are serialized as sorted JSON for stability.
    """
    # Sort the keys and sort the values within each key for stability
    sorted_params = {k: sorted(v) for k, v in sorted(params.items())}
    param_str = json.dumps(sorted_params, sort_keys=True)
    hash_value = hashlib.sha256(param_str.encode()).hexdigest()
    logger.debug("Computed hash %s for params: %s", hash_value[:12], sorted_params)
    return hash_value


def merge_urls(base_url: str, incoming_params: dict[str, list[str]]) -> str:
    """
    Merge incoming URL parameters into a base URL.

    Base URL parameters take precedence over incoming parameters.
    """
    parsed = urlparse(base_url)
    base_params = parse_qs(parsed.query, keep_blank_values=True)

    # Incoming params first, then base params override
    merged = dict(incoming_params)
    merged.update(base_params)

    # Rebuild the URL with merged parameters
    new_query = urlencode(merged, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    result = urlunparse(new_parsed)
    logger.debug(
        "Merged %d incoming params into base URL %s",
        len(incoming_params),
        parsed.netloc,
    )
    return result


def get_or_create_redirect(
    lookup_dir: Path,
    studies: list[Study],
    params: dict[str, list[str]],
) -> str:
    """
    Get an existing redirect URL or create a new one.

    Uses file locking to prevent race conditions.
    """
    url_hash = compute_hash(params)
    hash_file = lookup_dir / url_hash

    # Ensure lookup directory exists
    lookup_dir.mkdir(parents=True, exist_ok=True)

    logger.debug("Opening hash file: %s", hash_file)
    with open(hash_file, "a+") as f:
        try:
            logger.debug("Acquiring exclusive lock on %s", hash_file.name)
            fcntl.lockf(f, fcntl.LOCK_EX)
            f.seek(0)
            content = f.read().strip()

            if content:
                logger.debug("Cache hit for hash %s", url_hash[:12])
                return content

            # No existing redirect, create one
            logger.debug("Cache miss for hash %s, selecting new study", url_hash[:12])
            chosen = choose_study(studies)
            destination = merge_urls(chosen.url, params)

            f.write(destination + "\n")
            logger.debug("Created new redirect: %s -> %s", url_hash[:12], chosen.url)
            return destination
        finally:
            logger.debug("Releasing lock on %s", hash_file.name)
            fcntl.lockf(f, fcntl.LOCK_UN)
