"""
Unit tests for SQL tool functionality.
Tests database validation, tool registration, and error handling.
"""

import unittest
import tempfile
import sqlite3
from pathlib import Path
from tools import get_tool_by_name
from sql_engine import (
    execute_sql_query_impl, validate_database, 
    get_all_schemas, get_tables_relationships
)


class TestSQLToolRegistration(unittest.TestCase):
    """Test that SQL tool is properly registered."""
    
    def test_sql_tool_registered(self):
        """Verify execute_sql_query tool is in the registry."""
        tool = get_tool_by_name("execute_sql_query")
        self.assertIsNotNone(tool)
        self.assertEqual(tool["name"], "execute_sql_query")
        self.assertIn("database", tool["parameters"])
        self.assertIn("query", tool["parameters"])
    
    def test_sql_tool_has_callable_function(self):
        """Verify the tool has a callable function."""
        tool = get_tool_by_name("execute_sql_query")
        self.assertTrue(callable(tool["fn"]))


class TestDatabaseValidation(unittest.TestCase):
    """Test database validation logic."""
    
    def setUp(self):
        """Create a temporary test database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite"
        
        # Create a simple test database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT
            )
        """)
        cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_validate_existing_database(self):
        """Test validation of existing database."""
        result = validate_database(str(self.db_path))
        self.assertTrue(result["success"])
    
    def test_validate_nonexistent_database(self):
        """Test validation fails for nonexistent database."""
        result = validate_database("/nonexistent/path/db.sqlite")
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_execute_simple_query(self):
        """Test executing a simple SELECT query."""
        result = execute_sql_query_impl(str(self.db_path), "SELECT * FROM users")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["result"]), 2)
        self.assertEqual(result["row_count"], 2)
    
    def test_execute_query_with_invalid_database(self):
        """Test query execution with invalid database path."""
        result = execute_sql_query_impl("/nonexistent/db.sqlite", "SELECT 1")
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_execute_malformed_sql(self):
        """Test query execution with malformed SQL."""
        result = execute_sql_query_impl(str(self.db_path), "SELECT * FROM nonexistent_table")
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_execute_parameterized_query(self):
        """Test parameterized query execution."""
        result = execute_sql_query_impl(
            str(self.db_path),
            "SELECT * FROM users WHERE name = ?",
            ["Alice"]
        )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["result"]), 1)
        self.assertIn("Alice", result["result"][0])
    
    def test_schema_introspection(self):
        """Test schema introspection returns table information."""
        schemas = get_all_schemas(str(self.db_path))
        self.assertIn("users", schemas)
        self.assertIn("id", schemas)
        self.assertIn("name", schemas)
        self.assertIn("email", schemas)
    
    def test_relationships_introspection(self):
        """Test relationship introspection (no relationships in simple schema)."""
        relationships = get_tables_relationships(str(self.db_path))
        # Simple schema has no relationships
        self.assertIsNotNone(relationships)


class TestSQLToolErrorHandling(unittest.TestCase):
    """Test error handling in SQL tool."""
    
    def test_empty_query_result(self):
        """Test handling of empty query results."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / "test.sqlite"
        
        # Create test database with empty table
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE empty_table (id INTEGER)")
        conn.commit()
        conn.close()
        
        try:
            result = execute_sql_query_impl(str(db_path), "SELECT * FROM empty_table")
            self.assertTrue(result["success"])
            self.assertEqual(result["row_count"], 0)
            self.assertEqual(result["result"], [])
        finally:
            temp_dir.cleanup()
    
    def test_response_format_consistency(self):
        """Test that response format is consistent across success/failure."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / "test.sqlite"
        
        # Create test database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        
        try:
            # Test successful response
            success_result = execute_sql_query_impl(str(db_path), "SELECT * FROM test")
            self.assertIn("success", success_result)
            self.assertIn("query", success_result)
            self.assertIn("database", success_result)
            
            # Test failure response
            failure_result = execute_sql_query_impl("/bad/path.sqlite", "SELECT 1")
            self.assertIn("success", failure_result)
            self.assertIn("error", failure_result)
        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
