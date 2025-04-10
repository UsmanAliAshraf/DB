import os
import json

# Folder where all databases will be stored
DB_DIR = "data"

# Create data directory if it doesn't exist
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def load_collection(db_name, collection_name):
    """
    Load a collection from a JSON file within a database.
    If the file doesn't exist, creates a new empty collection.
    
    Args:
        db_name (str): Name of the database
        collection_name (str): Name of the collection to load
    Returns:
        list: List of documents in the collection
    """
    # Ensure database directory exists
    db_path = os.path.join(DB_DIR, db_name)
    if not os.path.exists(db_path):
        os.makedirs(db_path)
    
    # Full path to collection file
    collection_path = os.path.join(db_path, f"{collection_name}.json")

    # If file doesn't exist, create an empty one
    if not os.path.exists(collection_path):
        with open(collection_path, 'w') as f:
            json.dump([], f)  # Start with empty list

    # Read and return the data (list of documents)
    with open(collection_path, 'r') as f:
        return json.load(f)

def save_collection(db_name, collection_name, data):
    """
    Save a collection to a JSON file within a database.
    
    Args:
        db_name (str): Name of the database
        collection_name (str): Name of the collection to save
        data (list): List of documents to save
    """
    # Ensure database directory exists
    db_path = os.path.join(DB_DIR, db_name)
    if not os.path.exists(db_path):
        os.makedirs(db_path)
    
    # Full path to collection file
    collection_path = os.path.join(db_path, f"{collection_name}.json")
    
    with open(collection_path, 'w') as f:
        json.dump(data, f, indent=4)  # Save with proper formatting
