import os
import sys
import unittest
from unittest.mock import patch

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from free_lunch import current_time, fetch_url, web_search

from free_lunch.tools import build_langchain_tools

try:
    from langchain_core.tools import tool as _langchain_tool
except ImportError:
    _langchain_tool = None


class FakeDDGS:
    def text(self, query, max_results=5):
        return [
            {
                "title": "Free Lunch AI",
                "href": "https://example.com/free-lunch",
                "body": "A fallback router for free-tier model APIs.",
            },
            {
                "title": "LangGraph Search",
                "href": "https://example.com/langgraph",
                "body": "Plug tools directly into agent graphs.",
            },
        ]

    def extract(self, url, fmt="text_markdown"):
        return {
            "url": url,
            "content": f"# Example\n\nFetched as {fmt}.",
        }


class WebToolsTest(unittest.TestCase):
    @patch("free_lunch.tools.DDGS", return_value=FakeDDGS())
    def test_web_search_returns_clean_results(self, _mock_ddgs):
        result = web_search("free lunch ai", max_results=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Free Lunch AI")
        self.assertEqual(result[0]["url"], "https://example.com/free-lunch")
        self.assertEqual(result[0]["snippet"], "A fallback router for free-tier model APIs.")

    @patch("free_lunch.tools._fetch_jina", return_value="# Example\n\nRendered by Jina.")
    def test_fetch_url_uses_jina_first(self, _mock_jina):
        result = fetch_url("https://example.com")

        self.assertEqual(result["url"], "https://example.com")
        self.assertIn("Rendered by Jina.", result["content"])

    @patch("free_lunch.tools.DDGS", return_value=FakeDDGS())
    @patch("free_lunch.tools._fetch_jina", side_effect=httpx.HTTPError("rate limited"))
    def test_fetch_url_falls_back_to_ddgs_on_jina_error(self, _mock_jina, _mock_ddgs):
        result = fetch_url("https://example.com")

        self.assertEqual(result["url"], "https://example.com")
        self.assertIn("Fetched as text_markdown.", result["content"])

    def test_current_time_returns_expected_keys(self):
        result = current_time("UTC")

        self.assertEqual(result["timezone"], "UTC")
        self.assertIn("date", result)
        self.assertIn("weekday", result)
        self.assertIn("time", result)

    @unittest.skipIf(_langchain_tool is None, "langchain-core not installed")
    @patch("free_lunch.tools._fetch_jina", return_value="# Example\n\nRendered by Jina.")
    @patch("free_lunch.tools.DDGS", return_value=FakeDDGS())
    def test_build_langchain_tools_are_ready_to_use(self, _mock_ddgs, _mock_jina):
        web_search_tool, fetch_url_tool, current_time_tool = build_langchain_tools(
            web_search, fetch_url, current_time
        )

        content = web_search_tool.invoke({"query": "free lunch ai", "max_results": 2})
        self.assertIn("Search query: free lunch ai", content)
        self.assertIn("https://example.com/free-lunch", content)

        page = fetch_url_tool.invoke({"url": "https://example.com"})
        self.assertIn("Rendered by Jina.", page)

        now = current_time_tool.invoke({"timezone": "UTC"})
        self.assertIn("Date:", now)
        self.assertIn("Timezone: UTC", now)

    @unittest.skipIf(_langchain_tool is None, "langchain-core not installed")
    def test_build_langchain_tools_defaults_to_all(self):
        tools = build_langchain_tools()
        self.assertEqual(len(tools), 3)


if __name__ == "__main__":
    unittest.main()
