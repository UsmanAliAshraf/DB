import re
import json
from db import MyDB

def process_query(command_str):
    """
    Main function to process a raw MongoDB-like command string.
    It parses the command and performs the appropriate DB operation.
    """
    try:
        # Parse the command string
        operation, collection_name, params = parse_raw_query(command_str)

        if not operation or not collection_name:
            return "❌ Invalid query format. Please check syntax."

        # Create DB instance
        db = MyDB("my_database", collection_name)

        # --- FIND Operation ---
        if operation == "find":
            result = db.find(params)
            return json.dumps(result, indent=2) if result else "🔍 No documents found."

        # --- INSERT Operation ---
        elif operation == "insert":
            db.insert(params)
            return "✅ Document inserted."

        # --- UPDATE Operation ---
        elif operation == "update":
            db.update(params['query'], params['update'])
            return "🔁 Document(s) updated."

        # --- DELETE Operation ---
        elif operation == "delete":
            db.delete(params)
            return "🗑️ Document(s) deleted."

        else:
            return f"❌ Unsupported operation: {operation}"

    except json.JSONDecodeError as je:
        return f"❌ JSON parsing error: {str(je)}"
    except Exception as e:
        return f"❌ General error: {str(e)}"

def parse_raw_query(query_str):
    """
    Parses a raw MongoDB-like string (e.g., db.users.find({...})) into
    operation, collection, and parameters.

    Returns:
        tuple: (operation, collection_name, params)
    """
    query_str = query_str.strip().replace('\n', ' ').replace('\t', ' ')
    
    # Regex: db.collection.operation(params)
    pattern = r'^db\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\((.*)\)$'
    match = re.match(pattern, query_str)

    if not match:
        return None, None, None

    collection_name = match.group(1)
    operation = match.group(2)
    params_str = match.group(3)

    params = {}

    try:
        if operation == 'find':
            params = json.loads(params_str.replace("'", '"')) if params_str else {}

        elif operation == 'insert':
            params = json.loads(params_str.replace("'", '"'))

        elif operation == 'update':
            # Match: {query}, {update}
            update_pattern = r'^\s*({.*?})\s*,\s*({.*})\s*$'
            update_match = re.match(update_pattern, params_str)

            if not update_match:
                return None, None, None

            query = json.loads(update_match.group(1).replace("'", '"'))
            update = json.loads(update_match.group(2).replace("'", '"'))
            params = {'query': query, 'update': update}

        elif operation == 'delete':
            params = json.loads(params_str.replace("'", '"'))

        else:
            return None, None, None

        return operation, collection_name, params

    except json.JSONDecodeError:
        return None, None, None

def format_query_examples():
    """
    Return sample query strings users can try.
    """
    examples = [
        "db.users.find({name: 'John'})",
        "db.users.find({})",
        "db.users.insert({name: 'Alice', age: 25})",
        "db.users.update({id: 1}, {$set: {age: 30}})",
        "db.users.delete({id: 1})"
    ]
    return "\n".join([f"  {ex}" for ex in examples])
