---
name: browser-automation
description: Capture webpage screenshots and automate headless browser navigation for visual validation and web research.
---

# Browser Automation Skill

This skill teaches agents when and how to capture screenshots and perform browser-based visual tasks using the `take_screenshot` tool.

## Purpose

Use this skill when you need to:
- Capture the visual state of a webpage, web application, or localhost service
- Gather visual evidence or screenshots for documentation and reports
- Verify whether a web service is online and rendering properly
- Provide visual inputs for multimodal inspection or cross-validation

## Tool Definition

```json
{
  "tool": "take_screenshot",
  "params": {
    "url": "https://news.ycombinator.com",
    "output_dir": "playwright_images",
    "timeout": 30000
  }
}
```

### Parameter Reference

- `url` (string, required): The target webpage URL (e.g., `https://example.com` or `localhost:8000`). Automatically prepends `https://` if the scheme is omitted.
- `output_dir` (string, optional): Directory to save the PNG screenshot (default: `playwright_images`).
- `timeout` (integer, optional): Maximum page load timeout in milliseconds (default: `30000` = 30 seconds).

### Standard Response Format

Successful capture response:
```json
{
  "success": true,
  "url": "https://example.com",
  "screenshot_path": "playwright_images/example.com.png",
  "output_directory": "playwright_images"
}
```

Failure response:
```json
{
  "success": false,
  "url": "https://invalid.example",
  "error": "Browser error: net::ERR_NAME_NOT_RESOLVED"
}
```

## Recommended Workflow

### Step 1: Validate URL and Network Target
- Ensure the URL is properly formatted.
- For local services, verify the port and path (e.g., `http://localhost:5000/status`).

### Step 2: Invoke the Tool Call
Output the single-line JSON tool call:
```json
{"tool": "take_screenshot", "params": {"url": "https://example.com", "output_dir": "playwright_images"}}
```

### Step 3: Handle the Result
- On success: Confirm the saved image location (`screenshot_path`) and summarize the capture action.
- If Playwright is missing: Note that Playwright requires `pip install playwright && playwright install`.
- If timeout or navigation error occurs: Check if the site is reachable or increase the timeout parameter.

## Multi-Tool Chaining Patterns

Browser automation can be paired with other agent tools:
1. **Web to Database**: Take a screenshot of a dashboard or report page, then record metadata into a SQLite database with `execute_sql_query`.
2. **Web to File**: Capture a web screenshot, then write an audit log using `write_file`.

