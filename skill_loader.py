"""
Skill file loader for extracting task descriptions from SKILL.md files.

Parses SKILL.md files (YAML frontmatter + markdown content) and extracts
the skill description and instructions for use as agent task input.
"""

import re
from pathlib import Path
from typing import Dict, Optional


def load_skill_file(file_path: str) -> Dict[str, str]:
    """
    Load and parse a SKILL.md file.

    Extracts YAML frontmatter (name, description) and the main description
    section from the markdown body to use as agent task input.

    Args:
        file_path: Path to SKILL.md file

    Returns:
        Dictionary containing:
            - 'name': Skill name (from frontmatter or filename)
            - 'description': Extracted description text (from frontmatter + body sections)
            - 'body': Full markdown body content (everything after ---)

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file is not valid SKILL.md format
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {file_path}")

    if not path.name.endswith(".md"):
        raise ValueError(f"Skill file must be a markdown file: {file_path}")

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to read skill file: {str(e)}")

    # Parse YAML frontmatter and markdown body
    frontmatter, body = _parse_frontmatter(content)

    # Extract name from frontmatter or filename
    name = frontmatter.get("name", path.stem)

    # Extract description from frontmatter
    frontmatter_description = frontmatter.get("description", "")

    # Extract description from markdown body (first section or "Description" heading)
    body_description = _extract_description_from_body(body)

    # Combine frontmatter description and body description
    full_description = frontmatter_description
    if body_description:
        full_description = f"{full_description}\n\n{body_description}".strip()

    if not full_description:
        raise ValueError(
            f"No description found in {file_path}. "
            "SKILL.md must have 'description' in frontmatter or markdown body."
        )

    return {
        "name": name,
        "description": full_description,
        "body": body,
        "file_path": str(path.absolute()),
    }


def _parse_frontmatter(content: str) -> tuple:
    """
    Parse YAML frontmatter from markdown content.

    Extracts content between --- markers at the start of the file.

    Args:
        content: Full file content

    Returns:
        Tuple of (frontmatter_dict, body_text)
    """
    # Match frontmatter pattern: --- ... ---
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL
    )

    if not frontmatter_match:
        # No frontmatter found, treat entire content as body
        return {}, content

    frontmatter_text = frontmatter_match.group(1)
    body_text = frontmatter_match.group(2)

    # Parse YAML-like key: value pairs from frontmatter
    frontmatter_dict = _parse_yaml_simple(frontmatter_text)

    return frontmatter_dict, body_text


def _parse_yaml_simple(yaml_text: str) -> Dict[str, str]:
    """
    Simple YAML parser for frontmatter (supports basic key: value format).

    Args:
        yaml_text: YAML frontmatter text

    Returns:
        Dictionary of key-value pairs
    """
    result = {}
    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            # Remove surrounding quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            result[key] = value

    return result


def _extract_description_from_body(body: str) -> str:
    """
    Extract meaningful description content from markdown body.

    Looks for:
    1. First paragraph/section before any major headings
    2. A "Description" section if it exists
    3. Content after headings like "Use when", "Purpose", etc.

    Args:
        body: Markdown body content

    Returns:
        Extracted description text or empty string
    """
    if not body.strip():
        return ""

    lines = body.split("\n")
    description_lines = []
    in_description = False

    for i, line in enumerate(lines):
        # Look for description-related headings
        if re.match(r"^#+\s+(Description|Purpose|Overview|Use when)", line, re.IGNORECASE):
            in_description = True
            # Skip the heading line itself
            continue

        if in_description:
            # Stop at next heading
            if re.match(r"^#+\s+", line):
                break
            # Collect content until next heading
            if line.strip():
                description_lines.append(line)

    # If no explicit description section found, take first non-empty paragraph
    if not description_lines:
        for line in lines:
            if line.strip() and not re.match(r"^#+\s+", line):
                description_lines.append(line)
                break

    return "\n".join(description_lines).strip()
