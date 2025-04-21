# scrape_pkg/src/scrape_pkg/link_filters.py
"""
Reusable URL‑filter helpers.
"""
import re
from urllib.parse import urlparse

RAW_SOURCE_REGEX = re.compile(r"(/_sources/|/raw/|/source/|/_static/|/_downloads/)")
SOURCE_FILE_REGEX = re.compile(
    r"\.(md|rst|ipynb|py|txt|json|xml|cpp|h|c|js|css)\.txt$"
)
MEDIA_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
)
ALLOWED_EXTENSIONS = (".html", "/", "")


def should_skip_url(url: str) -> bool:
    lower = url.lower()
    if RAW_SOURCE_REGEX.search(lower) or SOURCE_FILE_REGEX.search(lower):
        return True
    if any(lower.endswith(ext) for ext in MEDIA_EXTENSIONS):
        return True
    parsed = urlparse(lower)
    return not any(parsed.path.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def is_html_doc(url: str) -> bool:
    parsed = urlparse(url)
    return any(parsed.path.endswith(ext) for ext in (".html", "/", ""))


def should_follow_url(url: str, include: list[str], exclude: list[str]) -> bool:
    parsed = urlparse(url)
    path = parsed.path
    for ex in exclude:
        if path.startswith(ex):
            return False
    if include:
        return any(path.startswith(inc) for inc in include)
    return True
