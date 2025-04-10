import re
import json
from db import MyDB

def process_query(command_str, collection_name):
    db = MyDB(collection_name)

    try:
        command_str = command_str.strip()

        # --- INSERT Query Parser ---
        if command_str.upper().startswith("INSERT"):
            # Regex to extract the JSON object after INSERT keyword
            match = re.search(r"INSERT\s+({.*})", command_str, re.IGNORECASE)
            if match:
                json_data = match.group(1)  # Group 1 contains the JSON string
                doc = json.loads(json_data)  # Convert JSON string to Python dict
                db.insert(doc)
                return "✅ Document inserted."
            else:
                return "❌ Invalid INSERT format. Use: INSERT {json_object}"

        # --- UPDATE Query Parser ---
        elif command_str.upper().startswith("UPDATE"):
            # Regex to extract two JSON objects in sequence (query and update)
            match = re.search(r"UPDATE\s+({.*?})\s+({.*})", command_str, re.IGNORECASE)
            # Breakdown:
            # {.*?} - non-greedy match for the first JSON object (query)
            # {.*}  - greedy match for the second JSON object (update)
            if match:
                query_str = match.group(1)
                update_str = match.group(2)

                query = json.loads(query_str)
                update = json.loads(update_str)

                db.update(query, update)
                return "🔁 Document(s) updated."
            else:
                return "❌ Invalid UPDATE format. Use: UPDATE {query} {update_doc}"

        # FIND and DELETE
        else:
            return "❌ Unsupported or not implemented yet."

    except json.JSONDecodeError as je:
        return f"❌ JSON parsing error: {str(je)}"
    except Exception as e:
        return f"❌ General error: {str(e)}"

def parse_raw_query(query_str):
    """
    Parse a raw MongoDB-like query string into operation and parameters using regex.
    
    Args:
        query_str (str): Raw query string (e.g., "db.users.find({name: 'John'})")
    Returns:
        tuple: (operation, collection_name, params)
    """
    # Remove whitespace and newlines
    query_str = query_str.strip().replace('\n', ' ').replace('\t', ' ')
    
    # Basic pattern matching for MongoDB-like queries
    # Pattern: db.collection.operation(params)
    pattern = r'^db\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\((.*)\)$'
    match = re.match(pattern, query_str)
    
    if not match:
        return None, None, None
    
    # Extract collection name and operation
    collection_name = match.group(1)
    operation = match.group(2)
    params_str = match.group(3)
    
    # Parse parameters based on operation
    params = {}
    
    if operation == 'find':
        # Handle empty find query
        if params_str == '{}':
            params = {}
        else:
            # Parse find query parameters 
            try:
                # Replace single quotes with double quotes for JSON parsing
                params = json.loads(params_str.replace("'", '"'))
            except json.JSONDecodeError:
                return None, None, None
    
    elif operation == 'insert':
        # Parse insert document
        try:
            params = json.loads(params_str.replace("'", '"'))
        except json.JSONDecodeError:
            return None, None, None
    
    elif operation == 'update':
        # Parse update query and update values
        # Pattern: {query}, {update}
        update_pattern = r'^\s*({.*?})\s*,\s*({.*})\s*$'
        update_match = re.match(update_pattern, params_str)
        
        if update_match:
            try:
                query = json.loads(update_match.group(1).replace("'", '"'))
                update = json.loads(update_match.group(2).replace("'", '"'))
                params = {'query': query, 'update': update}
            except json.JSONDecodeError:
                return None, None, None
        else:
            return None, None, None
    
    elif operation == 'delete':
        # Parse delete query
        try:
            params = json.loads(params_str.replace("'", '"'))
        except json.JSONDecodeError:
            return None, None, None
    
    else:
        # Unsupported operation
        return None, None, None
    
    return operation, collection_name, params

def format_query_examples():
    """
    Return formatted examples of valid queries.  
    
    Returns:
        str: Formatted examples
    """
    examples = [
        "db.users.find({name: 'John'})",
        "db.users.find({})",
        "db.users.insert({name: 'John', age: 30})",
        "db.users.update({id: 1}, {$set: {age: 31}})",
        "db.users.delete({id: 1})"
    ]
    
    return "\n".join([f"  {example}" for example in examples])
