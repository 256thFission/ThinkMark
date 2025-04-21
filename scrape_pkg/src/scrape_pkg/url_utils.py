# scrape_pkg/src/scrape_pkg/utils/url_utils.py
"""
URL helpers shared by spider & pipelines.
"""
from urllib.parse import urldefrag, urlparse, urlunparse
from slugify import slugify


def normalize_url(url: str) -> str:
    url, _ = urldefrag(url)
    p = urlparse(url)
    if p.path.endswith("/index.html"):
        p = p._replace(path=p.path[: -len("/index.html")])
    elif p.path.endswith("/") and len(p.path) > 1:
        p = p._replace(path=p.path[:-1])
    return urlunparse(p)


def slugify_path(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/")
    return "index" if not path else slugify(path.lstrip("/"))


def url_to_title(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/")
    if not path:
        return "Home"
    last = path.split("/")[-1]
    return last.replace("-", " ").replace("_", " ").title()
