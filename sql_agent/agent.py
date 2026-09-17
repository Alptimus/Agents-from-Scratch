import re
from prompts import SQL_PROMPT, RESPONSE_PROMPT
from chat_gemini import get_model
from schemas import get_all_schemas, get_tables_relationships, get_query_results

db_location = 'database/'
db_name = 'us_salaries.sqlite'
database = db_location + db_name

model = get_model()

def get_llm_response(model, prompt):
    chat = model.start_chat()
    response = chat.send_message(prompt)
    response.resolve()
    return response.text

def get_streamed_llm_response(model, prompt):
    chat = model.start_chat()
    for chunk in chat.send_message(prompt, stream=True):
        yield chunk.text.strip()

def parse_llm_sql_query(sql):
    pattern = r'```(?:\w*)\s*([\s\S]*?)```'
    match = re.search(pattern, sql)
    return match.group(1) if match else None

def main(model, query):
    tables = get_all_schemas(database)
    relationships = get_tables_relationships(database)

    print(tables)
    print(relationships)

    prompt = SQL_PROMPT.format(database_name=db_name, tables=tables, relationships=relationships, query=query)

    text = get_llm_response(model, prompt)

    parsed_sql = parse_llm_sql_query(text)

    print(parsed_sql)

    results = get_query_results(database, parsed_sql)

    print(results)
    print(type(results))
    # exit()



    # res_prompt = RESPONSE_PROMPT.format(results=results, tables=tables, relationships=relationships, query=query)
    # res_prompt = RESPONSE_PROMPT.format(results=results, query=query)

    # for text in get_streamed_llm_response(model, res_prompt):
    #     print(text, end=' ')
    # print()

if __name__ == '__main__':
    # query = "List all albums that are longer than 2 minutes."
    # query = "Name all artists that have albums in the database along with its artists in a table format."
    # query = "List the five tracks with the highest unit prices."
    # query = "Calculate how many tracks are associated with each genre. get all of the columns"
    # query = "Sum up sales for each album to find the total revenue."

    query = "Get salaries of all employees who have salary over 500k"

    main(model, query)
    pass