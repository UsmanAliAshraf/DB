import re
import json

def parse_raw_query(query_str):
    """
    Parses a raw MongoDB-style string (e.g., db.users.find({...})) into:
    - operation (find, insert, update, delete, create_collection, insert_many, create_index, drop_index)
    - collection name
    - parameters (dict or list)

    Supports:
    - find({query})
    - insert({doc})
    - insertMany([{doc1}, {doc2}, ...])
    - update({query}, {update})
    - delete({query})
    - createCollection()
    - createIndex({"field": 1}, {"type": "btree"})
    - dropIndex("field")

    Returns:
        tuple: (operation: str, collection_name: str, params: dict or list)
    """
    # Clean up the string: remove newlines, tabs
    query_str = query_str.strip().replace('\n', ' ').replace('\t', ' ')
    
    # Regex pattern: db.collection.operation(params)
    pattern = r'^db\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\((.*)\)$'
    match = re.match(pattern, query_str)

    if not match:
        return None, None, None

    collection_name = match.group(1)
    operation = match.group(2)
    params_str = match.group(3).strip()

    try:
        # Handle createCollection (no params)
        if operation == 'createCollection':
            if params_str:
                return None, None, None
            return 'create_collection', collection_name, {}
            
        # Handle createIndex
        if operation == 'createIndex':
            params_str = normalize_mongo_json(params_str)
            try:
                field_spec = json.loads(params_str)
                if not isinstance(field_spec, dict) or len(field_spec) != 1:
                    return None, None, None
                field_name = list(field_spec.keys())[0]
                return 'create_index', collection_name, {'field': field_name}
            except:
                return None, None, None

        # Handle dropIndex
        if operation == 'dropIndex':
            params_str = normalize_mongo_json(params_str)
            try:
                field_name = json.loads(params_str)
                if not isinstance(field_name, str):
                    return None, None, None
                return 'drop_index', collection_name, {'field': field_name}
            except:
                return None, None, None

        # Handle insertMany (expects a list)
        if operation == 'insertMany':
            params_str = normalize_mongo_json(params_str)
            docs = json.loads(params_str)
            if not isinstance(docs, list):
                return None, None, None
            return 'insert_many', collection_name, docs

        # Normalize Mongo-style single quotes to double quotes for JSON
        params_str = normalize_mongo_json(params_str)

        if operation == 'find':
            # Empty query means match all
            if not params_str:
                return operation, collection_name, {}
            return operation, collection_name, json.loads(params_str)

        elif operation == 'insert':
            return operation, collection_name, json.loads(params_str)

        elif operation == 'update':
            # Match two JSON objects separated by comma
            update_pattern = r'^\s*(\{.*?\})\s*,\s*(\{.*\})\s*$'
            update_match = re.match(update_pattern, params_str)
            if not update_match:
                return None, None, None

            query_part = json.loads(update_match.group(1))
            update_part = json.loads(update_match.group(2))
            return operation, collection_name, {'query': query_part, 'update': update_part}

        elif operation == 'delete':
            if not params_str:
                return operation, collection_name, {}
            return operation, collection_name, json.loads(params_str)

        else:
            return None, None, None

    except json.JSONDecodeError as e:
        print("JSON Decode Error:", e)
        return None, None, None


def normalize_mongo_json(text):
    """
    Converts Mongo-style single-quote JSON and unquoted keys into valid JSON.
    Also handles trailing commas and regex expressions as strings.
    """
    # Replace single quotes with double quotes (carefully)
    text = re.sub(r"'", r'"', text)

    # Replace unquoted keys with quoted keys: age: => "age":
    text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', text)

    # Handle trailing commas inside objects or arrays
    text = re.sub(r',\s*([\]}])', r'\1', text)

    return text

def parse_batch_queries(query_str):
    """
    Parses a string containing multiple MongoDB-style queries separated by semicolons.
    Returns (parsed_queries, error_info):
      - parsed_queries: list of parsed queries, or None if error
      - error_info: None if all good, or dict {"index": idx+1, "query": query, "error": "syntax error"}
    """
    queries = [q.strip() for q in query_str.split(';') if q.strip()]
    parsed_queries = []
    for idx, query in enumerate(queries):
        parsed = parse_raw_query(query)
        if parsed[0] is None:
            return None, {"index": idx+1, "query": query, "error": "syntax error"}
        parsed_queries.append(parsed)
    return parsed_queries, None
