from storage import load_collection, save_collection
from queryProcessor import match  # Import the query matching function

# Database class for a collection (like "users")
class MyDB:
    """
    A simple database class that implements basic CRUD operations.
    Each instance represents a collection (like a table in SQL databases).
    Data is persisted in JSON files in the data directory.
    """
    
    def __init__(self, db_name, collection_name):
        """
        Initialize a new database collection.
        Args:
            db_name (str): Name of the database
            collection_name (str): Name of the collection
        """
        self.db_name = db_name
        self.collection_name = collection_name
        self.data = load_collection(db_name, collection_name)  # Load existing docs or create new one if not available

    # Add new document
    def insert(self, doc):
        """
        Insert a new document into the collection.
        Args:
            doc (dict): Document to insert (must be a dictionary)
        """
        self.data.append(doc)
        save_collection(self.db_name, self.collection_name, self.data)

    # Find documents matching a query
    def find(self, query):
        """
        Find all documents that match the given query.
        Args:
            query (dict): Query criteria (e.g., {"name": "John"})
        Returns:
            list: List of matching documents
        """
        return [doc for doc in self.data if match(doc, query)]

    # Update documents matching query
    def update(self, query, update_values):
        """
        Update all documents that match the query.
        Args:
            query (dict): Query to match documents (e.g., {"id": 1})
            update_values (dict): Update operations (e.g., {"$set": {"age": 25}})
        """
        for doc in self.data:
            if match(doc, query):
                # For now, only supporting `$set` updates
                if "$set" in update_values:
                    doc.update(update_values["$set"])
        save_collection(self.db_name, self.collection_name, self.data)

    # Delete documents matching query
    def delete(self, query):
        """
        Delete all documents that match the query.
        Args:
            query (dict): Query to match documents for deletion
        """
        self.data = [doc for doc in self.data if not match(doc, query)]
        save_collection(self.db_name, self.collection_name, self.data)
