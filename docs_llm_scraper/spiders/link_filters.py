import re
from urllib.parse import urlparse

RAW_SOURCE_REGEX = re.compile(r"(/_sources/|/raw/|/source/|/_static/|/_downloads/)")
SOURCE_FILE_REGEX = re.compile(r"\.(md|rst|ipynb|py|txt|json|xml|cpp|h|c|js|css)\.txt$")
MEDIA_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.zip', '.tar', '.gz')
ALLOWED_EXTENSIONS = ('.html', '/', '')

def should_skip_url(url: str) -> bool:
    """
    Heuristically skip URLs that look like raw/source files, media, or non-HTML docs.
    """
    lower_url = url.lower()
    if RAW_SOURCE_REGEX.search(lower_url):
        return True
    if SOURCE_FILE_REGEX.search(lower_url):
        return True
    if any(lower_url.endswith(ext) for ext in MEDIA_EXTENSIONS):
        return True
    parsed = urlparse(lower_url)
    path = parsed.path
    if not any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return True
    return False


def is_html_doc(url: str) -> bool:
    """
    Check if URL is an HTML page or directory.
    """
    parsed = urlparse(url)
    path = parsed.path
    return any(path.endswith(ext) for ext in ('.html', '/', ''))


def should_follow_url(url: str, include_paths: list, exclude_paths: list) -> bool:
    """
    Determine if a URL should be followed based on include/exclude paths.
    """
    if not isinstance(url, str):
        url = str(url)
    parsed = urlparse(url)
    path = parsed.path
    for exclude in exclude_paths:
        if path.startswith(exclude):
            return False
    if include_paths:
        for include in include_paths:
            if path.startswith(include):
                return True
        return False
    return True