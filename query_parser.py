import re
import json

def parse_raw_query(query_str):
    """
    Parses a raw MongoDB-style string (e.g., db.users.find({...})) into:
    - operation (find, insert, update, delete)
    - collection name
    - parameters (dict)

    Supports:
    - find({query})
    - insert({doc})
    - update({query}, {update})
    - delete({query})

    Returns:
        tuple: (operation: str, collection_name: str, params: dict)
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
