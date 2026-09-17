import re
import sqlite3
from prompts import SQL_PROMPT, RESPONSE_PROMPT
from chat_gemini import get_model
from schemas import get_all_schemas, get_tables_relationships, get_query_results

db_location = 'dbs/'
db_name = 'chinook.db'
database = db_location + db_name

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

    # query = "List all tracks that are longer than 40 minutes."
    query = "Name all artists that have albums in the database along with its artists in a table format."
    # query = "List the five tracks with the highest unit prices."
    # query = "Calculate how many tracks are associated with each genre."
    # query = "Sum up sales for each album to find the total revenue."

    prompt = SQL_PROMPT.format(database_name=db_name, tables=tables, relationships=relationships, query=query)

    # print(prompt, end='\n\n')

    text = get_llm_response(model, prompt)
    parsed_sql = parse_llm_sql_query(text)

    # print(parsed_sql)

    results = get_query_results(database, parsed_sql)

    # print(results)
    # print(len(results))
    # for result in results:
    #     print(result)

    res_prompt = RESPONSE_PROMPT.format(results=results, tables=tables, relationships=relationships, query=query)
    # res_prompt = RESPONSE_PROMPT.format(results=results, query=query)

    # print(res_prompt, end='\n\n')

    text = get_llm_response(model, res_prompt)

    print(text.strip())