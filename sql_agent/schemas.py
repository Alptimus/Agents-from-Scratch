import sqlite3

def get_query_results(database, query, params=None):
    with sqlite3.connect(database) as conn:
        cur = conn.cursor()
        cur.execute(query, params) if params else cur.execute(query)
        results = cur.fetchall()
    return results

# def list_tables(database):
#     included_tables = ['albums', 'artists', 'customers', 'employees', 'genres', 
#                        'invoices', 'invoice_items', 'media_types', 'playlists', 
#                        'playlist_track', 'tracks']
#     placeholders = ','.join(['?'] * len(included_tables))
#     tables = get_query_results(database, f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders});", included_tables)
#     return [table[0] for table in tables]

def list_tables(database):
    query = """
      SELECT name
        FROM sqlite_master
       WHERE type='table'
         AND name NOT LIKE 'sqlite_%'
      ORDER BY name;
    """
    return [row[0] for row in get_query_results(database, query)]


def get_table_schema(database, table):
    schema = get_query_results(database, f"PRAGMA table_info('{table}');")
    return schema

def get_foreign_keys(database, table):
    foreign_keys = get_query_results(database, f"PRAGMA foreign_key_list('{table}');")
    return foreign_keys

def get_all_schemas(database):
    return "\n".join(
        f"Table: {table} -> [columns:type] ({', '.join(f'{column[1]}: {column[2]}' for column in get_table_schema(database, table))})"
        for table in list_tables(database)
    )

def get_tables_relationships(database):
    return "\n".join(
        f"{table}.{fk[3]} -> {fk[2]}.{fk[4]}"
        for table in list_tables(database)
        for fk in get_foreign_keys(database, table)
        if fk
    )

def print_all_schemas(database):
    tables = list_tables(database)
    for table in tables:
        print(f"Schema for table: {table}")
        schema = get_table_schema(database, table)
        for column in schema:
            print(f"Column: {column[1]} | Type: {column[2]} | Not Null: {column[3]} | Default Value: {column[4]}")
        print()

def print_table_relationships(database):
    tables = list_tables(database)
    relationships = []
    
    for table in tables:
        foreign_keys = get_foreign_keys(database, table)
        if foreign_keys:
            for fk in foreign_keys:
                # fk[2] = referenced table, fk[3] = referencing column, fk[4] = referenced column
                relationships.append((table, fk[3], fk[2], fk[4]))
    
    if relationships:
        print("Table Relationships (Foreign Key Constraints):")
        for relationship in relationships:
            print(f"{relationship[0]}.{relationship[1]} -> {relationship[2]}.{relationship[3]}")
    else:
        print("No foreign key relationships found.")

if __name__ == '__main__':
    database = 'databases/chinook.db'

    print_all_schemas(database)
    print_table_relationships(database)
    # s = get_all_schemas(database)
    # print(s)
    # r = get_tables_relationships(database)
    # print(r)
    pass