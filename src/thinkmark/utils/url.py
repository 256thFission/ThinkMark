"""URL handling utilities."""

from urllib.parse import urlparse, urljoin, urldefrag
from typing import Optional, List
import re
from slugify import slugify # Moved import here

def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments and ensuring no trailing slashes on the path, except for the root."""
    url_no_frag, _ = urldefrag(url)
    parsed = urlparse(url_no_frag)
    
    current_path = parsed.path
    
    # If the path is not the root path ("/") and ends with a slash, remove the trailing slash.
    if current_path != "/" and current_path.endswith("/"):
        new_path = current_path.rstrip("/")
    else:
        # Preserve the path if it's the root ("/") or already has no trailing slash (e.g. "/path", "")
        new_path = current_path
        
    return parsed._replace(path=new_path, fragment="", params="", query=parsed.query).geturl()


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

def url_to_filename(url: str, is_dir: bool = False) -> str:
    """Convert URL to a valid filename or directory name.
    
    Args:
        url: The URL to convert
        is_dir: If True, returns a directory name without file extension
        
    Returns:
        A filesystem-safe string derived from the URL
    """
    # slugify is now imported at the module level
    parsed = urlparse(url)
    domain = parsed.netloc or 'site'  # Fallback if no netloc
    path = parsed.path.strip("/")
    
    # For directory names, we want just the domain
    if is_dir:
        return slugify(domain)
        
    # For filenames, include the path components
    if path:
        # Replace slashes in path with hyphens before slugifying
        processed_path = path.replace('/', '-')
        return f"{slugify(domain)}-{slugify(processed_path)}.html"
    return f"{slugify(domain)}.html"


def get_site_directory(url: str, base_dir: str = None) -> str:
    """Get the filesystem path for a site's directory.
    
    Args:
        url: The site URL
        base_dir: Optional base directory (defaults to current directory)
        
    Returns:
        Absolute path to the site's directory
    """
    from pathlib import Path
    
    dir_name = url_to_filename(url, is_dir=True)
    if base_dir:
        return str(Path(base_dir).resolve() / dir_name)
    return dir_name
