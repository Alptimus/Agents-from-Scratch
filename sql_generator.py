"""
SQL Generator: LLM-based SQL query generation from natural language.
Provider-agnostic: works with Ollama, Gemini, or any LLM backend.
"""

import re
import json
from typing import Any, Dict, Optional
from sql_engine import get_all_schemas, get_tables_relationships


# SQL Generation Prompts
SQL_GENERATION_PROMPT = """You are an Expert SQL Developer proficient in writing optimized SQLite queries.
You will be provided with a database schema and relationships, then generate SQL queries based on natural language requests.

**Database Schema:**

{schemas}

**Table Relationships:**

{relationships}

**Instructions:**
- Only provide SQL queries in markdown code blocks (```sql ... ```)
- Write secure, optimized queries
- Do not include explanations, only the SQL query

**User Request:**
{query}

**Response (SQL only, in markdown code block):**
"""

SQL_RESPONSE_PROMPT = """You are a SQL Analysis Assistant. Provide a clear, professional answer to the user's query based on the SQL results.

**User Query:** {query}

**SQL Results:**
{results}

**Response (plain text, no markdown):**
"""


def parse_sql_from_response(response_text: str) -> Optional[str]:
    """
    Extract SQL query from markdown code block in LLM response.
    Looks for ```sql ... ``` or ``` ... ``` blocks.
    """
    # Try to find sql code block
    pattern = r'```(?:sql|SQL)?\s*([\s\S]*?)```'
    match = re.search(pattern, response_text)
    if match:
        return match.group(1).strip()
    
    # Fallback: look for any triple backtick block
    match = re.search(r'```\s*([\s\S]*?)```', response_text)
    if match:
        return match.group(1).strip()
    
    return None


def generate_sql_prompt(database: str, query: str) -> Dict[str, Any]:
    """
    Generate the LLM prompt for SQL query generation.
    Returns dict with prompt and metadata.
    """
    try:
        schemas = get_all_schemas(database)
        relationships = get_tables_relationships(database)
        
        prompt = SQL_GENERATION_PROMPT.format(
            schemas=schemas,
            relationships=relationships,
            query=query
        )
        
        return {
            "success": True,
            "prompt": prompt,
            "database": database,
            "user_query": query
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error generating prompt: {str(e)}"
        }


def generate_response_prompt(query: str, results: list) -> Dict[str, Any]:
    """
    Generate the LLM prompt for formatting SQL results.
    Converts raw query results into human-readable format.
    """
    try:
        # Format results as readable text
        if isinstance(results, list) and len(results) > 0:
            if isinstance(results[0], (tuple, list)):
                results_text = "\n".join(str(row) for row in results)
            else:
                results_text = str(results)
        else:
            results_text = "No results found"
        
        prompt = SQL_RESPONSE_PROMPT.format(
            query=query,
            results=results_text
        )
        
        return {
            "success": True,
            "prompt": prompt,
            "user_query": query,
            "result_count": len(results) if isinstance(results, list) else 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error generating response prompt: {str(e)}"
        }


def format_sql_results(results: list, query: str, max_rows: int = 10) -> str:
    """
    Format SQL query results in a readable way.
    Useful for displaying to users or passing to LLM.
    """
    if not results:
        return "No results found for the query."
    
    lines = []
    lines.append(f"Query: {query}")
    lines.append(f"Total rows: {len(results)}")
    lines.append("")
    
    # Show first max_rows
    display_results = results[:max_rows]
    for i, row in enumerate(display_results, 1):
        if isinstance(row, (tuple, list)):
            lines.append(f"Row {i}: {row}")
        else:
            lines.append(f"Row {i}: {str(row)}")
    
    if len(results) > max_rows:
        lines.append(f"... and {len(results) - max_rows} more rows")
    
    return "\n".join(lines)
