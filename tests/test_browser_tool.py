"""
Unit tests for browser automation and take_screenshot tool.
Tests URL sanitization, validation, tool registration, and mocked Playwright behavior.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import browser_automation
from browser_automation import (
    ensure_output_directory,
    sanitize_url_for_filename,
    take_screenshot_impl,
    validate_url,
)
from tools import get_tool_by_name


class TestBrowserToolRegistration(unittest.TestCase):
    """Test take_screenshot tool registration in tools.py."""

    def test_tool_registered(self):
        """Verify take_screenshot is in tool registry with proper schema."""
        tool = get_tool_by_name("take_screenshot")
        self.assertIsNotNone(tool)
        self.assertEqual(tool["name"], "take_screenshot")
        self.assertIn("url", tool["parameters"])
        self.assertIn("output_dir", tool["parameters"])
        self.assertIn("timeout", tool["parameters"])
        self.assertTrue(callable(tool["fn"]))


class TestBrowserUrlHelpers(unittest.TestCase):
    """Test URL sanitization and validation functions."""

    def test_sanitize_url_basic(self):
        """Verify schemes and slashes are sanitized for filenames."""
        self.assertEqual(
            sanitize_url_for_filename("https://example.com/page"),
            "example.com_page"
        )
        self.assertEqual(
            sanitize_url_for_filename("http://example.org/api/v1"),
            "example.org_api_v1"
        )

    def test_sanitize_url_query_and_hash(self):
        """Verify query parameters and hash fragments are sanitized."""
        url = "https://example.com/search?q=test&lang=en#results"
        sanitized = sanitize_url_for_filename(url)
        self.assertNotIn("?", sanitized)
        self.assertNotIn("&", sanitized)
        self.assertNotIn("#", sanitized)
        self.assertEqual(sanitized, "example.com_search_q_test_lang_en_results")

    def test_sanitize_url_max_length(self):
        """Verify long URLs are truncated with ellipsis."""
        long_url = "https://example.com/" + ("a" * 150)
        sanitized = sanitize_url_for_filename(long_url, max_length=50)
        self.assertEqual(len(sanitized), 53)  # 50 + len("...")
        self.assertTrue(sanitized.endswith("..."))

    def test_validate_url_valid(self):
        """Verify valid URLs pass validation."""
        self.assertTrue(validate_url("https://example.com")["success"])
        self.assertTrue(validate_url("http://localhost:3000")["success"])
        self.assertTrue(validate_url("www.python.org")["success"])
        self.assertTrue(validate_url("docs.python.org/3/")["success"])

    def test_validate_url_invalid(self):
        """Verify invalid URLs return error."""
        self.assertFalse(validate_url("")["success"])
        self.assertFalse(validate_url("   ")["success"])
        self.assertFalse(validate_url("not_a_valid_url")["success"])
        self.assertFalse(validate_url(None)["success"])


class TestBrowserDirectoryHelper(unittest.TestCase):
    """Test output directory creation."""

    def test_ensure_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "screenshots" / "nested"
            res = ensure_output_directory(str(target))
            self.assertTrue(res["success"])
            self.assertTrue(target.exists())
            self.assertTrue(target.is_dir())


class TestTakeScreenshotImpl(unittest.TestCase):
    """Test take_screenshot_impl with mocked Playwright and fallback conditions."""

    def test_missing_playwright_dependency(self):
        """Verify informative error message when Playwright is unavailable."""
        with patch.object(browser_automation, "sync_playwright", None):
            res = take_screenshot_impl("https://example.com")
            self.assertFalse(res["success"])
            self.assertIn("Playwright is not installed", res["error"])

    def test_invalid_url_returns_error(self):
        """Verify invalid URL fails before attempting browser operations."""
        res = take_screenshot_impl("not_a_valid_url")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    def test_mocked_playwright_success(self):
        """Verify full screenshot flow with mocked Playwright browser and page."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_playwright_ctx = MagicMock()
        mock_playwright_ctx.chromium.launch.return_value = mock_browser

        mock_sync_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright_ctx

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(browser_automation, "sync_playwright", mock_sync_playwright):
                res = take_screenshot_impl(
                    url="example.com/dashboard",
                    output_dir=temp_dir,
                    timeout=5000
                )

                self.assertTrue(res["success"])
                self.assertEqual(res["url"], "https://example.com/dashboard")
                self.assertTrue(res["screenshot_path"].endswith("example.com_dashboard.png"))
                self.assertEqual(res["output_directory"], temp_dir)

                # Verify browser calls
                mock_playwright_ctx.chromium.launch.assert_called_once_with(headless=True)
                mock_page.goto.assert_called_once_with("https://example.com/dashboard", timeout=5000)
                mock_page.screenshot.assert_called_once()
                mock_context.close.assert_called_once()
                mock_browser.close.assert_called_once()

    def test_mocked_playwright_navigation_error(self):
        """Verify browser navigation errors are caught and reported cleanly."""
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("net::ERR_CONNECTION_REFUSED")
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_playwright_ctx = MagicMock()
        mock_playwright_ctx.chromium.launch.return_value = mock_browser

        mock_sync_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright_ctx

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(browser_automation, "sync_playwright", mock_sync_playwright):
                res = take_screenshot_impl(
                    url="https://unreachable-site.local",
                    output_dir=temp_dir
                )

                self.assertFalse(res["success"])
                self.assertIn("Browser error", res["error"])
                self.assertIn("ERR_CONNECTION_REFUSED", res["error"])
                # Ensure browser is closed even on exception
                mock_browser.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

