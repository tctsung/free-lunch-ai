"""Built-in direct-use utilities plus optional LangChain tool wrappers."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
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


def _fetch_jina(url: str) -> str:
    """Fetch a URL through the keyless Jina Reader; returns markdown content."""
    response = httpx.get(_JINA_READER + url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.text.strip()


def fetch_url(url: str) -> dict[str, str]:
    """
    Read a web page when a specific URL already exists.

    Jina Reader is the primary fetcher because it renders pages in a real
    browser server-side, so it returns full content for JavaScript/SPA sites
    (e.g. Airbnb) that plain extraction sees as empty or a "enable JavaScript"
    stub. If Jina errors — most often its ~20 req/min keyless rate limit — we
    fall back to DDGS extraction, which is unlimited and works for static pages.

    Args:
        url: Web page URL to extract.
    """
    try:
        return {"url": url, "content": _fetch_jina(url)}
    except httpx.HTTPError:
        result = DDGS().extract(url)
        return {"url": result["url"], "content": result["content"]}


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


def _require(package: str) -> Any:
    """Import an optional ``[rag]`` parser, or raise a clear install hint."""
    try:
        return import_module(package)
    except ImportError:
        raise ImportError(
            f"This file type needs the '{package}' package. Install the RAG extra "
            'with: pip install "free-lunch-ai[rag] @ '
            'git+https://github.com/tctsung/free-lunch-ai.git"'
        )


def _read_pdf(path: Path) -> str:
    pdfplumber = _require("pdfplumber")
    with pdfplumber.open(path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    # Separate pages so the LLM can see document structure / cite page numbers.
    return "\n\n".join(
        f"## Page {i}\n\n{text.strip()}" for i, text in enumerate(pages, start=1) if text.strip()
    )


def _read_docx(path: Path) -> str:
    mammoth = _require("mammoth")
    with path.open("rb") as handle:
        return mammoth.convert_to_markdown(handle).value.strip()


def _read_html(path: Path) -> str:
    markdownify = _require("markdownify")
    html = path.read_text(encoding="utf-8", errors="replace")
    return markdownify.markdownify(html).strip()


def _md_cell(value: Any) -> str:
    """Stringify a spreadsheet cell for a Markdown table (escape pipes/newlines)."""
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _read_xlsx(path: Path) -> str:
    openpyxl = _require("openpyxl")
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    blocks = []
    for name in workbook.sheetnames:
        rows = [r for r in workbook[name].iter_rows(values_only=True) if any(c is not None for c in r)]
        if not rows:
            continue  # skip empty sheets
        width = max(len(r) for r in rows)
        # First non-empty row is the header; pad ragged rows to a uniform width.
        table = []
        for row in rows:
            cells = [_md_cell(c) for c in row] + [""] * (width - len(row))
            table.append("| " + " | ".join(cells) + " |")
        table.insert(1, "| " + " | ".join(["---"] * width) + " |")
        blocks.append(f"## {name}\n\n" + "\n".join(table))
    return "\n\n".join(blocks)


def read_file(path: str) -> dict[str, str]:
    """
    Read a local document and return its text as Markdown for an LLM.

    Dispatches by file extension: ``.pdf`` (pdfplumber), ``.docx`` (mammoth),
    ``.xlsx`` (openpyxl, one Markdown table per sheet), and ``.html``/``.htm``
    (markdownify) are converted to Markdown. Any other suffix (``.md``, ``.txt``,
    ``.csv``, ``.json``, ``.py``, ``.log`` …) is read as UTF-8 text. The Markdown
    parsers are optional — install them with the ``[rag]`` extra. Runs fully
    locally; no network calls.

    Args:
        path: Path to a local file.

    Returns:
        ``{"path", "content", "format"}`` where ``format`` is the file suffix.
    """
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(f"No such file: {file_path}")

    suffix = file_path.suffix.lower()
    converters = {
        ".pdf": _read_pdf,
        ".docx": _read_docx,
        ".xlsx": _read_xlsx,
        ".html": _read_html,
        ".htm": _read_html,
    }
    if suffix in converters:
        content = converters[suffix](file_path)
    else:
        content = file_path.read_text(encoding="utf-8", errors="replace").strip()

    return {"path": str(file_path), "content": content, "format": suffix.lstrip(".")}


def build_langchain_tools(*functions: Callable[..., Any]) -> list[Any]:
    """
    Build LangChain tools from plain functions.

    Args:
        functions: Plain functions such as ``web_search``, ``fetch_url``, or
            ``read_file``. If omitted, builds all bundled tools.
    """
    if _langchain_tool is None:
        raise ImportError(
            'LangChain is not installed. Install with: '
            'pip install "free-lunch-ai[langchain] @ git+https://github.com/tctsung/free-lunch-ai.git"'
        )
    if not functions:
        functions = (web_search, fetch_url, current_time, read_file)

    tools = []
    for fn in functions:
        if fn is web_search:
            tools.append(_wrap_langchain_tool("web_search", _tool_web_search))
        elif fn is fetch_url:
            tools.append(_wrap_langchain_tool("fetch_url", _tool_fetch_url))
        elif fn is current_time:
            tools.append(_wrap_langchain_tool("current_time", _tool_current_time))
        elif fn is read_file:
            tools.append(_wrap_langchain_tool("read_file", _tool_read_file))
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


def _tool_read_file(path: str) -> str:
    """
    Read a local document (PDF, DOCX, XLSX, HTML, or text) as Markdown.

    Args:
        path: Path to a local file.
    """
    return read_file(path)["content"]


__all__ = [
    "web_search",
    "fetch_url",
    "current_time",
    "read_file",
    "build_langchain_tools",
]
