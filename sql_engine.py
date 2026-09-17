"""
SQL Engine: Backend-agnostic database operations for SQLite.
Provides schema introspection and query execution with standard tool response format.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_query_results(database: str, query: str, params: Optional[List] = None) -> List[tuple]:
    """Execute a raw SQL query and return results as list of tuples."""
    try:
        with sqlite3.connect(database) as conn:
            cur = conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur.fetchall()
    except sqlite3.Error as e:
        raise Exception(f"Database error: {str(e)}")


def list_tables(database: str) -> List[str]:
    """List all non-system tables in the database."""
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """
    return [row[0] for row in get_query_results(database, query)]


def get_table_schema(database: str, table: str) -> List[tuple]:
    """Get schema information for a table using PRAGMA table_info."""
    try:
        return get_query_results(database, f"PRAGMA table_info('{table}');")
    except Exception as e:
        raise Exception(f"Error getting schema for table '{table}': {str(e)}")


def get_foreign_keys(database: str, table: str) -> List[tuple]:
    """Get foreign key constraints for a table using PRAGMA foreign_key_list."""
    try:
        return get_query_results(database, f"PRAGMA foreign_key_list('{table}');")
    except Exception as e:
        raise Exception(f"Error getting foreign keys for table '{table}': {str(e)}")


def get_all_schemas(database: str) -> str:
    """Get formatted schema information for all tables."""
    try:
        tables = list_tables(database)
        schemas = []
        for table in tables:
            columns = get_table_schema(database, table)
            col_str = ", ".join(f"{col[1]}: {col[2]}" for col in columns)
            schemas.append(f"Table: {table} -> [columns:type] ({col_str})")
        return "\n".join(schemas)
    except Exception as e:
        raise Exception(f"Error getting schemas: {str(e)}")


def get_tables_relationships(database: str) -> str:
    """Get formatted foreign key relationships between tables."""
    try:
        relationships = []
        for table in list_tables(database):
            for fk in get_foreign_keys(database, table):
                if fk:
                    # fk format: (id, seq, table, from, to, on_delete, on_update, match)
                    relationships.append(f"{table}.{fk[3]} -> {fk[2]}.{fk[4]}")
        return "\n".join(relationships) if relationships else "No relationships found"
    except Exception as e:
        raise Exception(f"Error getting relationships: {str(e)}")


def validate_database(database: str) -> Dict[str, Any]:
    """Validate that database file exists and is accessible."""
    try:
        path = Path(database)
        if not path.exists():
            return {"success": False, "error": f"Database file not found: {database}"}
        if not path.is_file():
            return {"success": False, "error": f"Path is not a file: {database}"}
        
        # Try to connect and verify it's a valid SQLite database
        with sqlite3.connect(database) as conn:
            conn.execute("PRAGMA schema_version")
        
        return {"success": True}
    except sqlite3.Error as e:
        return {"success": False, "error": f"Not a valid SQLite database: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error validating database: {str(e)}"}


def execute_sql_query_impl(database: str, query: str, params: Optional[List] = None) -> Dict[str, Any]:
    """
    Execute SQL query against SQLite database.
    Returns standard tool response format: {"success": bool, "result": [...] or "error": str}
    """
    # Validate database first
    validation = validate_database(database)
    if not validation["success"]:
        return validation
    
    try:
        # Execute query
        results = get_query_results(database, query, params)
        
        # Format results
        return {
            "success": True,
            "query": query,
            "database": database,
            "result": results,
            "row_count": len(results)
        }
    except sqlite3.Error as e:
        return {
            "success": False,
            "query": query,
            "database": database,
            "error": f"SQL Error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "query": query,
            "database": database,
            "error": f"Error executing query: {str(e)}"
        }


def get_schema_for_tool(database: str) -> Dict[str, Any]:
    """
    Get comprehensive schema information for a database.
    Used to provide context to LLM for SQL generation.
    """
    try:
        validation = validate_database(database)
        if not validation["success"]:
            return validation
        
        schemas = get_all_schemas(database)
        relationships = get_tables_relationships(database)
        
        return {
            "success": True,
            "database": database,
            "schemas": schemas,
            "relationships": relationships
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting schema: {str(e)}"
        }
