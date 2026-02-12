import re
import ipaddress
from urllib.parse import urlparse

ALLOWED_SORT_COLUMNS = {"title", "created_at", "author"}
ALLOWED_FETCH_HOSTS = {"api.github.com", "example.com"}
ALLOWED_FORMATS = {"png", "jpg", "webp"}
ALLOWED_REPORTS = {"daily", "weekly", "monthly"}
GITHUB_USER_RE = re.compile(r'^[A-Za-z0-9-]{1,39}$')
FILE_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,20}$')

URL_CATALOG: dict[str, str] = {
    "github_api": "https://api.github.com",
    "example": "https://example.com",
    "httpbin": "https://httpbin.org/get",
}


def is_private_ip(host: str) -> bool:
    """Return True if host resolves to a private/loopback/link-local address."""
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        # Not a bare IP — check well-known private hostnames
        private_hosts = {"localhost", "metadata.google.internal"}
        return host.lower() in private_hosts


def validate_url(url: str) -> str:
    """
    Validate that url uses https, its host is in the allowlist,
    and it does not point to a private IP. Returns the url if valid,
    raises ValueError otherwise.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs allowed, got scheme={parsed.scheme!r}")
    host = parsed.hostname or ""
    if host not in ALLOWED_FETCH_HOSTS:
        raise ValueError(f"Host {host!r} not in allowlist")
    if is_private_ip(host):
        raise ValueError(f"Host {host!r} resolves to a private address")
    return url
