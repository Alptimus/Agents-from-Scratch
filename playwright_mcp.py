import sys
import os
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright, url: str) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto(url)

    # Sanitize URL for filename
    url_filename = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_").replace("?", "_").replace("=", "_").replace("&", "_")
    if len(url_filename) > 100:
        url_filename = url_filename[:100] + "..."

    screenshot_dir = "playwright images"
    os.makedirs(screenshot_dir, exist_ok=True)
    screenshot_path = os.path.join(screenshot_dir, f"{url_filename}.png")

    page.screenshot(path=screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")

    # ---------------------
    context.close()
    browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playwright_mcp.py <URL>")
        sys.exit(1)

    website_url = sys.argv[1]
    with sync_playwright() as playwright:
        run(playwright, website_url)
