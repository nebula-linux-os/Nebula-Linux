"""Web tools — actually read pages, not just search snippets.

Adds:
  fetch_page(url)  — GET a URL, strip HTML to readable text, return it.
  fetch_json(url)  — GET a URL, parse as JSON, return the object.

Both are safe (read-only), no confirmation needed. Kept lightweight: no
Selenium, no headless browser — those belong to a different tier if
they're ever needed.
"""
from __future__ import annotations

import html
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests

from .version import __version__

_USER_AGENT = f"Nova-Agent/{__version__} (+https://github.com/nebula-linux-os/Nebula-Linux)"
_MAX_BYTES = 2_000_000       # cap raw response at 2 MB
_MAX_CHARS = 12_000          # cap text extract at ~12k chars (~3k tokens)
_MAX_REDIRECTS = 5


def _valid_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _blocked_reason(url: str) -> str | None:
    """Return why `url` must not be fetched, or None if it's a public host.

    These tools are ungated and driven by model output (which can be
    prompt-injected by a page it read), so they must not reach loopback
    (Nova's own API, Ollama), the LAN (routers, NAS admin pages) or cloud
    metadata endpoints. Every address the hostname resolves to is checked.
    """
    if not _valid_http_url(url):
        return "url must start with http:// or https://"
    host = urlparse(url).hostname
    if not host:
        return "url has no host"
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        return f"cannot resolve {host}: {e}"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            return f"refusing to fetch non-public address {ip} ({host})"
    return None


def _safe_get(url: str, **kwargs) -> requests.Response:
    """requests.get that re-validates the target on every redirect hop."""
    for _ in range(_MAX_REDIRECTS + 1):
        reason = _blocked_reason(url)
        if reason:
            raise requests.RequestException(reason)
        resp = requests.get(url, allow_redirects=False, **kwargs)
        if resp.is_redirect and "Location" in resp.headers:
            url = urljoin(url, resp.headers["Location"])
            resp.close()
            continue
        return resp
    raise requests.RequestException(f"more than {_MAX_REDIRECTS} redirects")


_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|iframe|svg|form|nav|footer|header|aside)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANKLINES_RE = re.compile(r"\n{3,}")


def _html_to_text(body: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", body)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(h[1-6]|li|tr|div)>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANKLINES_RE.sub("\n\n", text)
    return text.strip()


def _extract_title(body: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    return html.unescape(m.group(1).strip()) if m else ""


def fetch_page(url: str, max_chars: int = _MAX_CHARS) -> dict:
    """Fetch a web page and return its readable text content."""
    if not _valid_http_url(url):
        return {"error": "url must start with http:// or https://"}
    try:
        resp = _safe_get(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html,*/*"},
            timeout=15,
            stream=True,
        )
    except requests.RequestException as e:
        return {"error": f"request failed: {e}"}

    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "url": resp.url}

    ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    raw = resp.raw.read(_MAX_BYTES, decode_content=True)
    resp.close()
    try:
        body = raw.decode(resp.encoding or "utf-8", errors="replace")
    except LookupError:
        body = raw.decode("utf-8", errors="replace")

    if "html" in ctype or "<html" in body[:1000].lower():
        title = _extract_title(body)
        text = _html_to_text(body)
    else:
        title = ""
        text = body

    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]

    return {
        "url": resp.url,
        "title": title,
        "content_type": ctype,
        "chars": len(text),
        "truncated": truncated,
        "text": text,
    }


def fetch_json(url: str) -> dict:
    """Fetch a URL and return the parsed JSON body."""
    if not _valid_http_url(url):
        return {"error": "url must start with http:// or https://"}
    try:
        resp = _safe_get(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"request failed: {e}"}
    try:
        return {"url": resp.url, "data": resp.json()}
    except ValueError:
        return {"error": "response was not valid JSON", "url": resp.url,
                "preview": resp.text[:500]}


WEB_TOOL_FUNCTIONS = {
    "fetch_page": fetch_page,
    "fetch_json": fetch_json,
}

WEB_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch a web page and return its readable text content (HTML tags stripped, whitespace collapsed). Use to answer questions from a specific URL, or after web_search returns a promising link. Truncated at 12k chars.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http(s) URL of the page to fetch"},
                    "max_chars": {"type": "integer", "description": "Truncate text at this many characters (default 12000)"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_json",
            "description": "Fetch a URL and parse the response as JSON. Use for REST APIs, config endpoints, /api/... URLs. Fails with 'not valid JSON' if the response isn't JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http(s) URL returning JSON"},
                },
                "required": ["url"],
            },
        },
    },
]
