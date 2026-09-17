---
name: sql-agent
description: Query and analyze SQLite databases using schema introspection, query execution, and relational data analysis.
---

# SQL Agent Skill

This skill teaches agents when and how to interact with SQLite databases using the `execute_sql_query` tool.

## Purpose

Use this skill when you need to:
- Explore the tables and schema of a SQLite database
- Retrieve data from relational tables to answer user questions
- Perform aggregations, joins, filtering, and statistical analysis on database contents
- Validate data consistency or cross-reference database records with other sources

## Tool Definition

```json
{
  "tool": "execute_sql_query",
  "params": {
    "database": "databases/us_salaries.sqlite",
    "query": "SELECT name, salary FROM employees WHERE salary > 100000 ORDER BY salary DESC LIMIT 10",
    "params": []
  }
}
```

### Parameter Reference

- `database` (string, required): File path to the SQLite database (e.g., `databases/us_salaries.sqlite` or `databases/chinook.db`).
- `query` (string, required): The SQL statement to execute.
- `params` (array, optional): Parameter values when using parameterized queries with `?` placeholders.

### Standard Response Format

Successful query response:
```json
{
  "success": true,
  "query": "SELECT count(*) FROM employees",
  "database": "databases/us_salaries.sqlite",
  "result": [[15243]],
  "row_count": 1
}
```

Failure response:
```json
{
  "success": false,
  "query": "SELECT * FROM missing_table",
  "database": "databases/us_salaries.sqlite",
  "error": "Error executing query: no such table: missing_table"
}
```

## Recommended 4-Step Workflow

When tasked with querying a database, follow this systematic workflow:

### Step 1: Introspect Schema
If you do not already know the exact schema, run a query to discover the available tables:
```sql
SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';
```
Then inspect the columns of the relevant table(s):
```sql
PRAGMA table_info('table_name');
```

### Step 2: Formulate the SQL Query
- Write explicit column names instead of `SELECT *` where possible to keep responses clean.
- Use `LIMIT` clauses when inspecting unknown or large tables.
- Use parameterized queries `?` when values originate from untrusted or variable user inputs.
- Join tables using explicit foreign key constraints identified during schema introspection.

### Step 3: Execute the Tool Call
Output the single-line JSON tool call:
```json
{"tool": "execute_sql_query", "params": {"database": "databases/chinook.db", "query": "SELECT title, name FROM albums JOIN artists ON albums.artist_id = artists.artist_id LIMIT 5"}}
```

### Step 4: Interpret and Present Results
- Convert raw tabular tuples into human-readable answers.
- If the query returns empty results `[]`, state that no matching records were found and verify if filtering criteria was too strict.
- If an error occurs, inspect the error message, adjust column/table names, and retry.

## Safety Guidelines

- Only execute read queries (`SELECT`, `PRAGMA`) unless explicitly instructed by the user to modify records.
- Always verify that the database file path exists before running complex queries.

