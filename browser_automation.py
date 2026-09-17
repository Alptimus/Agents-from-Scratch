"""
Browser Automation: Playwright-based web screenshot tool.
Provides headless browser functionality for web data extraction and validation.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def sanitize_url_for_filename(url: str, max_length: int = 100) -> str:
    """
    Convert URL to safe filename by replacing special characters.
    Examples:
        "https://example.com/page" -> "example.com_page"
        "https://example.com/page?id=123&name=test" -> "example.com_page_id_123_na..."
    """
    # Remove scheme
    url = url.replace("https://", "").replace("http://", "")
    
    # Replace special characters with underscores
    for ch in ["/", ":", "?", "=", "&", "#"]:
        url = url.replace(ch, "_")
    
    # Trim to max length
    if len(url) > max_length:
        url = url[:max_length] + "..."
    
    return url


def ensure_output_directory(output_dir: str) -> Dict[str, Any]:
    """Create output directory if it doesn't exist."""
    try:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(path.absolute())}
    except Exception as e:
        return {"success": False, "error": f"Error creating directory: {str(e)}"}


def take_screenshot_impl(url: str, output_dir: str = "playwright_images", timeout: int = 30000) -> Dict[str, Any]:
    """
    Take a screenshot of a web page using Playwright.
    
    Args:
        url: The URL to screenshot
        output_dir: Directory to save screenshots (default: playwright_images)
        timeout: Timeout in milliseconds (default: 30000ms = 30s)
    
    Returns:
        {"success": bool, "screenshot_path": str or "error": str}
    """
    # Validate URL input
    url_val = validate_url(url)
    if not url_val["success"]:
        return url_val

    # Check if playwright is available
    if sync_playwright is None:
        return {
            "success": False,
            "error": "Playwright is not installed. Install with: pip install playwright && playwright install"
        }
    
    try:
        # Validate URL format
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Ensure output directory exists
        dir_result = ensure_output_directory(output_dir)
        if not dir_result["success"]:
            return dir_result
        
        # Generate filename from URL
        filename = sanitize_url_for_filename(url)
        screenshot_path = os.path.join(output_dir, f"{filename}.png")
        
        # Launch browser and take screenshot
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()
                
                # Navigate to URL with timeout
                page.goto(url, timeout=timeout)
                
                # Take screenshot
                page.screenshot(path=screenshot_path)
                
                context.close()
                
                return {
                    "success": True,
                    "url": url,
                    "screenshot_path": screenshot_path,
                    "output_directory": output_dir
                }
            except Exception as e:
                return {
                    "success": False,
                    "url": url,
                    "error": f"Browser error: {str(e)}"
                }
            finally:
                browser.close()
    
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": f"Screenshot failed: {str(e)}"
        }


def validate_url(url: str) -> Dict[str, Any]:
    """Validate that URL is properly formatted."""
    try:
        if not isinstance(url, str) or len(url.strip()) == 0:
            return {"success": False, "error": "URL must be a non-empty string"}
        
        # Basic URL validation
        if not url.startswith(("http://", "https://", "www.")):
            if "." not in url:
                return {"success": False, "error": "Invalid URL format"}
        
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "error": f"URL validation error: {str(e)}"}
