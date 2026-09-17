"""
Comprehensive unit tests for database access, schema introspection,
and SQL generator utilities.
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sql_engine import (
    execute_sql_query_impl,
    get_all_schemas,
    get_foreign_keys,
    get_query_results,
    get_schema_for_tool,
    get_table_schema,
    get_tables_relationships,
    list_tables,
    validate_database,
)
from sql_generator import (
    format_sql_results,
    generate_response_prompt,
    generate_sql_prompt,
    parse_sql_from_response,
)


class TestDatabaseAccess(unittest.TestCase):
    """Tests for low-level database access and schema introspection."""

    def setUp(self):
        """Create a temporary SQLite database with relational schema."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_store.sqlite"

        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE artists (
                    artist_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE albums (
                    album_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist_id INTEGER,
                    FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
                );
            """)
            cur.execute("""
                CREATE TABLE tracks (
                    track_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    album_id INTEGER,
                    unit_price REAL DEFAULT 0.99,
                    FOREIGN KEY (album_id) REFERENCES albums(album_id)
                );
            """)
            # Insert sample data
            cur.execute("INSERT INTO artists (artist_id, name) VALUES (1, 'AC/DC')")
            cur.execute("INSERT INTO artists (artist_id, name) VALUES (2, 'Queen')")
            cur.execute("INSERT INTO albums (album_id, title, artist_id) VALUES (10, 'Back in Black', 1)")
            cur.execute("INSERT INTO albums (album_id, title, artist_id) VALUES (20, 'A Night at the Opera', 2)")
            cur.execute("INSERT INTO tracks (track_id, name, album_id, unit_price) VALUES (101, 'Hells Bells', 10, 0.99)")
            cur.execute("INSERT INTO tracks (track_id, name, album_id, unit_price) VALUES (102, 'Bohemian Rhapsody', 20, 1.29)")
            conn.commit()

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_list_tables(self):
        """Verify list_tables returns non-system tables in sorted order."""
        tables = list_tables(str(self.db_path))
        self.assertEqual(tables, ["albums", "artists", "tracks"])

    def test_get_table_schema(self):
        """Verify get_table_schema retrieves column metadata."""
        schema = get_table_schema(str(self.db_path), "artists")
        col_names = [col[1] for col in schema]
        self.assertIn("artist_id", col_names)
        self.assertIn("name", col_names)

    def test_get_foreign_keys(self):
        """Verify foreign key constraints are extracted correctly."""
        fks = get_foreign_keys(str(self.db_path), "albums")
        self.assertTrue(len(fks) > 0)
        # Check referenced table is artists and column is artist_id
        fk = fks[0]
        self.assertEqual(fk[2], "artists")
        self.assertEqual(fk[3], "artist_id")
        self.assertEqual(fk[4], "artist_id")

    def test_get_all_schemas(self):
        """Verify formatted schema string contains table names and columns."""
        schemas_str = get_all_schemas(str(self.db_path))
        self.assertIn("Table: artists", schemas_str)
        self.assertIn("Table: albums", schemas_str)
        self.assertIn("Table: tracks", schemas_str)
        self.assertIn("unit_price: REAL", schemas_str)

    def test_get_tables_relationships(self):
        """Verify relationship formatting includes parent-child mappings."""
        rels = get_tables_relationships(str(self.db_path))
        self.assertIn("albums.artist_id -> artists.artist_id", rels)
        self.assertIn("tracks.album_id -> albums.album_id", rels)

    def test_get_schema_for_tool(self):
        """Verify get_schema_for_tool bundle returns schemas and relationships."""
        res = get_schema_for_tool(str(self.db_path))
        self.assertTrue(res["success"])
        self.assertIn("schemas", res)
        self.assertIn("relationships", res)

    def test_validate_database_invalid_files(self):
        """Verify validate_database handles missing files, directories, and non-sqlite files."""
        # Directory instead of file
        res = validate_database(self.temp_dir.name)
        self.assertFalse(res["success"])
        self.assertIn("Path is not a file", res["error"])

        # Corrupted / non-sqlite file
        bad_file = Path(self.temp_dir.name) / "bad.sqlite"
        bad_file.write_text("not a sqlite database", encoding="utf-8")
        res = validate_database(str(bad_file))
        self.assertFalse(res["success"])

    def test_parameterized_query(self):
        """Verify parameterized queries work with integers, floats, and strings."""
        res = execute_sql_query_impl(
            str(self.db_path),
            "SELECT name, unit_price FROM tracks WHERE album_id = ? AND unit_price > ?",
            [20, 1.0]
        )
        self.assertTrue(res["success"])
        self.assertEqual(len(res["result"]), 1)
        self.assertEqual(res["result"][0][0], "Bohemian Rhapsody")


class TestSqlGenerator(unittest.TestCase):
    """Tests for SQL generator prompts and parsing functions."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("CREATE TABLE items (id INT, title TEXT)")
            conn.commit()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_sql_from_markdown_blocks(self):
        """Verify parsing SQL queries from various markdown block formats."""
        # ```sql block
        resp1 = "Here is the query:\n```sql\nSELECT * FROM items;\n```"
        self.assertEqual(parse_sql_from_response(resp1), "SELECT * FROM items;")

        # ```SQL block
        resp2 = "```SQL\nSELECT id FROM items WHERE id = 1\n```"
        self.assertEqual(parse_sql_from_response(resp2), "SELECT id FROM items WHERE id = 1")

        # generic ``` block
        resp3 = "Query:\n```\nSELECT count(*) FROM items\n```"
        self.assertEqual(parse_sql_from_response(resp3), "SELECT count(*) FROM items")

        # no block
        resp4 = "There is no code block here."
        self.assertIsNone(parse_sql_from_response(resp4))

    def test_generate_sql_prompt(self):
        """Verify SQL prompt generation incorporates schema and user query."""
        prompt_res = generate_sql_prompt(str(self.db_path), "Find all items")
        self.assertTrue(prompt_res["success"])
        self.assertIn("Table: items", prompt_res["prompt"])
        self.assertIn("Find all items", prompt_res["prompt"])

    def test_generate_response_prompt(self):
        """Verify response prompt generation formats query results."""
        results = [(1, "Item A"), (2, "Item B")]
        res = generate_response_prompt("List items", results)
        self.assertTrue(res["success"])
        self.assertIn("Item A", res["prompt"])
        self.assertEqual(res["result_count"], 2)

    def test_format_sql_results_truncation(self):
        """Verify result formatter truncates when row count exceeds max_rows."""
        many_results = [(i, f"Item {i}") for i in range(15)]
        formatted = format_sql_results(many_results, "SELECT * FROM items", max_rows=5)
        self.assertIn("Total rows: 15", formatted)
        self.assertIn("Row 5:", formatted)
        self.assertIn("... and 10 more rows", formatted)

        # Empty results
        empty_formatted = format_sql_results([], "SELECT * FROM items")
        self.assertEqual(empty_formatted, "No results found for the query.")


if __name__ == "__main__":
    unittest.main()

