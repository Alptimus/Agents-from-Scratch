"""
Legacy SQL Agent Prototype 2 (chinook.db).
Archived in sql_agent/legacy/ - use main.py with sql_agent/SKILL.md instead.
"""

import os
import re
import sqlite3
import sys
from pathlib import Path

# Ensure sql_agent and repo root are accessible on sys.path
current_dir = Path(__file__).resolve().parent
sql_agent_dir = current_dir.parent
repo_root = sql_agent_dir.parent

for p in [str(repo_root), str(sql_agent_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from sql_agent.prompts import SQL_PROMPT, RESPONSE_PROMPT
    from sql_agent.chat_gemini import get_model
    from sql_agent.schemas import get_all_schemas, get_tables_relationships, get_query_results
except ImportError:
    from prompts import SQL_PROMPT, RESPONSE_PROMPT
    from chat_gemini import get_model
    from schemas import get_all_schemas, get_tables_relationships, get_query_results

db_location = 'databases/'
db_name = 'chinook.db'
db_file = repo_root / db_location / db_name
database = str(db_file) if db_file.exists() else (db_location + db_name)

model = get_model()


def get_llm_response(model, prompt):
    chat = model.start_chat()
    response = chat.send_message(prompt)
    response.resolve()
    return response.text


def parse_llm_sql_query(sql):
    pattern = r'```(?:\w*)\s*([\s\S]*?)```'
    match = re.search(pattern, sql)
    return match.group(1) if match else None


if __name__ == '__main__':
    tables = get_all_schemas(database)
    relationships = get_tables_relationships(database)

    query = "Name all artists that have albums in the database along with its artists in a table format."

    prompt = SQL_PROMPT.format(database_name=db_name, tables=tables, relationships=relationships, query=query)

    text = get_llm_response(model, prompt)
    parsed_sql = parse_llm_sql_query(text)

    results = get_query_results(database, parsed_sql)

    res_prompt = RESPONSE_PROMPT.format(results=results, tables=tables, relationships=relationships, query=query)

    text = get_llm_response(model, res_prompt)

    print(text.strip())
