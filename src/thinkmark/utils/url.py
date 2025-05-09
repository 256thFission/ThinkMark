"""URL handling utilities."""

from urllib.parse import urlparse, urljoin, urldefrag
from typing import Optional, List
import re

def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments and trailing slashes."""
    # Remove fragment
    url, _ = urldefrag(url)

    # Remove trailing slash except for domain root
    parsed = urlparse(url)
    if parsed.path.rstrip("/") or not parsed.netloc:
        if parsed.path.endswith("/"):
            path = parsed.path.rstrip("/")
            url = url[:-len(parsed.path)] + path + url[-len(parsed.path) + len(path):]

    return url

def is_url_allowed(
    url: str,
    allowed_domains: Optional[List[str]] = None,
    include_paths: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None
) -> bool:
    """Check if URL is allowed based on domain and path rules."""
    parsed = urlparse(url)

    # Check domain
    if allowed_domains and parsed.netloc not in allowed_domains:
        return False

    # Check excluded paths
    if exclude_paths and any(parsed.path.startswith(path) for path in exclude_paths):
        return False

    # Check included paths
    if include_paths and not any(parsed.path.startswith(path) for path in include_paths):
        return False

    return True

def url_to_filename(url: str) -> str:
    """Convert URL to a valid filename."""
    from slugify import slugify

    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path.strip("/")

    if path:
        return f"{slugify(domain)}-{slugify(path)}.html"
    return f"{slugify(domain)}.html"
