"""Built-in direct-use utilities plus optional LangChain tool wrappers."""
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

import httpx
from ddgs import DDGS

# Keyless Jina Reader endpoint — renders JS pages server-side, returns clean
# markdown. Free at ~20 req/min without an API key. See INSTRUCTIONS.md.
_JINA_READER = "https://r.jina.ai/"

try:
    from langchain_core.tools import tool as _langchain_tool
except ImportError:
    _langchain_tool = None


def _compact_text(text: str) -> str:
    """Collapse extra whitespace so search snippets stay easy to read."""
    return " ".join(text.split()).strip()


def _render_search_results(query: str, results: list[dict[str, str]]) -> str:
    if not results:
        return f"Search query: {query}\nNo results found."

    lines = [f"Search query: {query}", ""]
    for index, item in enumerate(results, start=1):
        lines.append(f"{index}. {item['title']}")
        lines.append(f"Source: {item['url']}")
        if item["snippet"]:
            lines.append(item["snippet"])
        lines.append("")
    return "\n".join(lines).strip()


def _render_current_time(timezone: str | None = None) -> str:
    now = current_time(timezone)
    return (
        f"Date: {now['date']}\n"
        f"Weekday: {now['weekday']}\n"
        f"Time: {now['time']}\n"
        f"Timezone: {now['timezone']}"
    )


def _wrap_langchain_tool(name: str, fn: Callable[..., Any]) -> Any:
    return _langchain_tool(name)(fn)


def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """
    Search the web when recent external information is needed.

    Args:
        query: Search terms to run.
        max_results: Maximum number of results to return.

    Returns:
        Search results with title, source URL, and snippet.
    """
    results = DDGS().text(query, max_results=max_results)
    return [
        {
            "title": _compact_text(item.get("title", "")),
            "url": item.get("href", "").strip(),
            "snippet": _compact_text(item.get("body", "")),
        }
        for item in results
    ]


def _fetch_via_reader(url: str) -> str:
    """Fetch a URL through the keyless Jina Reader; returns markdown content."""
    response = httpx.get(_JINA_READER + url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.text.strip()


def fetch_url(url: str) -> dict[str, str]:
    """
    Read a web page when a specific URL already exists.

    Uses DDGS markdown extraction. JavaScript-rendered pages (SPAs) return no
    text via DDGS, so when that happens we retry once through the keyless Jina
    Reader, which renders the page server-side. A genuinely dead page (404,
    timeout) raises from DDGS — the reader would fail the same way.

    Args:
        url: Web page URL to extract.
    """
    result = DDGS().extract(url)
    content = result["content"]

    # DDGS returned HTTP 200 but no text — typical of JS/SPA pages.
    if not content.strip():
        try:
            content = _fetch_via_reader(url)
        except httpx.HTTPError:
            pass  # keep the empty result if the reader is also unavailable

    return {"url": result["url"], "content": content}


def current_time(timezone: str | None = None) -> dict[str, str]:
    """
    Get the current date, weekday, and time.

    Args:
        timezone: Optional IANA timezone like America/New_York.
    """
    now = datetime.now(ZoneInfo(timezone)) if timezone else datetime.now().astimezone()
    timezone_name = timezone or getattr(now.tzinfo, "key", None) or now.tzname() or "UTC"
    return {
        "date": now.date().isoformat(),
        "weekday": now.strftime("%A"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": timezone_name,
    }


def build_langchain_tools(*functions: Callable[..., Any]) -> list[Any]:
    """
    Build LangChain tools from plain functions.

    Args:
        functions: Plain functions such as ``web_search`` or ``fetch_url``.
            If omitted, builds all bundled tools.
    """
    if _langchain_tool is None:
        raise ImportError(
            'LangChain is not installed. Install with: '
            'pip install "free-lunch-ai[langchain] @ git+https://github.com/tctsung/free-lunch-ai.git"'
        )
    if not functions:
        functions = (web_search, fetch_url, current_time)

    tools = []
    for fn in functions:
        if fn is web_search:
            tools.append(_wrap_langchain_tool("web_search", _tool_web_search))
        elif fn is fetch_url:
            tools.append(_wrap_langchain_tool("fetch_url", _tool_fetch_url))
        elif fn is current_time:
            tools.append(_wrap_langchain_tool("current_time", _tool_current_time))
        else:
            tools.append(_langchain_tool(fn))
    return tools


def _tool_web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web when recent external information is needed.

    Args:
        query: Search terms to run.
        max_results: Maximum number of results to return.
    """
    return _render_search_results(query, web_search(query, max_results=max_results))


def _tool_fetch_url(url: str) -> str:
    """
    Read a web page when a specific URL already exists.

    Args:
        url: Web page URL to extract.
    """
    return fetch_url(url)["content"]


def _tool_current_time(timezone: str | None = None) -> str:
    """
    Get the current date, weekday, and time.

    Args:
        timezone: Optional IANA timezone like America/New_York.
    """
    return _render_current_time(timezone)


__all__ = [
    "web_search",
    "fetch_url",
    "current_time",
    "build_langchain_tools",
]
