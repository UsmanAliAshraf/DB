from db import MyDB
import json
import os
import shutil
from query_parser import parse_raw_query, format_query_examples

# Directory where all databases will be stored
DB_DIR = "data"

# Ensure the data directory exists
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def print_main_menu():
    """Display the main menu options"""
    print("\n=== Welcome to Doucment based DB ===")
    print("1. Create New Database")
    print("2. View Existing Databases")
    print("3. Open Query Editor")
    print("4. Exit")
    print("=======================")

def print_database_menu(db_name):
    """Display the database management menu"""
    print(f"\n=== Database: {db_name} ===")
    print("1. View Collections")
    print("2. Create New Collection")
    print("3. Rename Database")
    print("4. Delete Database")
    print("5. Back to Main Menu")
    print("=======================")

def print_collection_menu(db_name, collection_name):
    """Display the collection management menu"""
    print(f"\n=== Collection: {collection_name} in {db_name} ===")
    print("1. Insert Document")
    print("2. Find Documents")
    print("3. Update Document")
    print("4. Delete Document")
    print("5. Show All Documents")
    print("6. Back to Database Menu")
    print("=========================")

def print_query_editor_menu():
    """Display the query editor menu"""
    print("\n=== Query Editor ===")
    print("1. Select Database")
    print("2. Write Raw Query")
    print("3. Back to Main Menu")
    print("===================")

def get_database_name():
    """Get database name from user"""
    return input("Enter database name: ").strip()

def get_collection_name():
    """Get collection name from user"""
    return input("Enter collection name: ").strip()

def list_databases():
    """List all existing databases"""
    databases = [d for d in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, d))]
    if databases:
        print("\nExisting Databases:")
        for i, db in enumerate(databases, 1):
            print(f"{i}. {db}")
        return databases
    else:
        print("\nNo databases found.")
        return []

def create_database():
    """Create a new database"""
    db_name = get_database_name()
    db_path = os.path.join(DB_DIR, db_name)
    
    if os.path.exists(db_path):
        print(f"Database '{db_name}' already exists.")
        return None
    
    os.makedirs(db_path)
    print(f"Database '{db_name}' created successfully.")
    
    # Ask if user wants to create a collection
    create_collection = input("Do you want to create a collection in this database? (yes/no): ").strip().lower()
    if create_collection == 'yes':
        collection_name = get_collection_name()
        collection_path = os.path.join(db_path, f"{collection_name}.json")
        with open(collection_path, 'w') as f:
            json.dump([], f)
        print(f"Collection '{collection_name}' created successfully.")
    
    return db_name

def manage_database(db_name):
    """Manage an existing database"""
    db_path = os.path.join(DB_DIR, db_name)
    
    while True:
        print_database_menu(db_name)
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1':
            # View collections
            collections = [f.replace('.json', '') for f in os.listdir(db_path) if f.endswith('.json')]
            if collections:
                print("\nCollections:")
                for i, coll in enumerate(collections, 1):
                    print(f"{i}. {coll}")
            else:
                print("\nNo collections found in this database.")
        
        elif choice == '2':
            # Create new collection
            collection_name = get_collection_name()
            collection_path = os.path.join(db_path, f"{collection_name}.json")
            
            if os.path.exists(collection_path):
                print(f"Collection '{collection_name}' already exists.")
            else:
                with open(collection_path, 'w') as f:
                    json.dump([], f)
                print(f"Collection '{collection_name}' created successfully.")
        
        elif choice == '3':
            # Rename database
            new_name = input("Enter new database name: ").strip()
            new_path = os.path.join(DB_DIR, new_name)
            
            if os.path.exists(new_path):
                print(f"Database '{new_name}' already exists.")
            else:
                os.rename(db_path, new_path)
                print(f"Database renamed from '{db_name}' to '{new_name}'.")
                return new_name
        
        elif choice == '4':
            # Delete database
            confirm = input(f"Are you sure you want to delete database '{db_name}'? (yes/no): ").strip().lower()
            if confirm == 'yes':
                shutil.rmtree(db_path)
                print(f"Database '{db_name}' deleted successfully.")
                return None
            else:
                print("Deletion cancelled.")
        
        elif choice == '5':
            # Back to main menu
            return db_name
        
        else:
            print("Invalid choice. Please try again.")

def manage_collection(db_name, collection_name):
    """Manage a collection within a database"""
    db = MyDB(db_name, collection_name)
    
    while True:
        print_collection_menu(db_name, collection_name)
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '1':
            # Insert document
            print("\nEnter document data (key-value pairs)")
            print("Example: {'name': 'John', 'age': 25}")
            try:
                doc_str = input("Enter document (in JSON format): ")
                doc = json.loads(doc_str)
                db.insert(doc)
                print("Document inserted successfully!")
            except json.JSONDecodeError:
                print("Error: Invalid JSON format. Please use proper JSON syntax.")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == '2':
            # Find documents
            print("\nEnter query criteria")
            print("Example: {'name': 'John'} or {} for all documents")
            try:
                query_str = input("Enter query (in JSON format): ")
                query = json.loads(query_str)
                results = db.find(query)
                print("\nFound documents:")
                for doc in results:
                    print(json.dumps(doc, indent=2))
            except json.JSONDecodeError:
                print("Error: Invalid JSON format. Please use proper JSON syntax.")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == '3':
            # Update document
            print("\nEnter query to match documents to update")
            print("Example: {'id': 1}")
            try:
                query_str = input("Enter query (in JSON format): ")
                query = json.loads(query_str)
                
                print("\nEnter update values")
                print("Example: {'$set': {'age': 26}}")
                update_str = input("Enter update values (in JSON format):")
                update_values = json.loads(update_str)
                
                db.update(query, update_values)
                print("Documents updated successfully!")
            except json.JSONDecodeError:
                print("Error: Invalid JSON format. Please use proper JSON syntax.")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == '4':
            # Delete document
            print("\nEnter query to match documents to delete")
            print("Example: {'id': 1}")
            try:
                query_str = input("Enter query (in JSON format): ")
                query = json.loads(query_str)
                
                # Show matching documents before deletion
                matches = db.find(query)
                if matches:
                    print("\nDocuments to be deleted:")
                    for doc in matches:
                        print(json.dumps(doc, indent=2))
                    
                    confirm = input("\nAre you sure you want to delete these documents? (yes/no): ")
                    if confirm.lower() == 'yes':
                        db.delete(query)
                        print("Documents deleted successfully!")
                    else:
                        print("Deletion cancelled.")
                else:
                    print("No matching documents found.")
            except json.JSONDecodeError:
                print("Error: Invalid JSON format. Please use proper JSON syntax.")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == '5':
            # Show all documents
            try:
                results = db.find({})
                if results:
                    print(f"\nAll documents in {collection_name}:")
                    for doc in results:
                        print(json.dumps(doc, indent=2))
                else:
                    print("No documents found in the collection.")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == '6':
            # Back to database menu
            break
        
        else:
            print("Invalid choice. Please try again.")

def execute_raw_query(db_name, query_str):
    """
    Execute a raw MongoDB-like query.
    
    Args:
        db_name (str): Name of the database
        query_str (str): Raw query string
    """
    operation, collection_name, params = parse_raw_query(query_str)
    
    if operation is None:
        print("Error: Invalid query format.")
        print("Example formats:")
        print(format_query_examples())
        return
    
    # Check if collection exists
    db_path = os.path.join(DB_DIR, db_name)
    collection_path = os.path.join(db_path, f"{collection_name}.json")
    
    if not os.path.exists(collection_path):
        print(f"Error: Collection '{collection_name}' does not exist in database '{db_name}'.")
        return
    
    # Execute the operation
    db = MyDB(db_name, collection_name)
    
    try:
        if operation == 'find':
            results = db.find(params)
            print("\nResults:")
            for doc in results:
                print(json.dumps(doc, indent=2))
        
        elif operation == 'insert':
            db.insert(params)
            print("Document inserted successfully!")
        
        elif operation == 'update':
            db.update(params['query'], params['update'])
            print("Documents updated successfully!")
        
        elif operation == 'delete':
            # Show matching documents before deletion
            matches = db.find(params)
            if matches:
                print("\nDocuments to be deleted:")
                for doc in matches:
                    print(json.dumps(doc, indent=2))
                
                confirm = input("\nAre you sure you want to delete these documents? (yes/no): ")
                if confirm.lower() == 'yes':
                    db.delete(params)
                    print("Documents deleted successfully!")
                else:
                    print("Deletion cancelled.")
            else:
                print("No matching documents found.")
        
        else:
            print(f"Error: Unsupported operation '{operation}'.")
    
    except Exception as e:
        print(f"Error executing query: {str(e)}")

def query_editor():
    """Interactive query editor"""
    db_name = None
    
    while True:
        print_query_editor_menu()
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == '1':
            # Select database
            databases = list_databases()
            if databases:
                try:
                    db_index = int(input("Enter database number: ").strip()) - 1
                    if 0 <= db_index < len(databases):
                        db_name = databases[db_index]
                        print(f"Selected database: {db_name}")
                        
                        # List collections
                        db_path = os.path.join(DB_DIR, db_name)
                        collections = [f.replace('.json', '') for f in os.listdir(db_path) if f.endswith('.json')]
                        if collections:
                            print("\nAvailable collections:")
                            for coll in collections:
                                print(f"- {coll}")
                        else:
                            print("No collections found in this database.")
                    else:
                        print("Invalid database number.")
                except ValueError:
                    print("Please enter a valid number.")
            else:
                print("No databases available. Please create a database first.")
        
        elif choice == '2':
            # Write raw query
            if db_name is None:
                print("Please select a database first.")
            else:
                print("\n=== Raw Query Editor ===")
                print("Write your query in MongoDB-like syntax:")
                print("Examples:")
                print(format_query_examples())
                print("\nEnter your query (or 'exit' to go back):")
                
                query_str = input("> ")
                if query_str.lower() == 'exit':
                    continue
                
                execute_raw_query(db_name, query_str)
        
        elif choice == '3':
            # Back to main menu
            break
        
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main function to run the interactive CLI"""
    while True:
        print_main_menu()
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            # Create new database
            create_database()
        
        elif choice == '2':
            # View existing databases
            databases = list_databases()
            if databases:
                try:
                    db_index = int(input("Enter database number (0 to go back): ").strip()) - 1
                    if db_index == -1:
                        continue
                    if 0 <= db_index < len(databases):
                        db_name = databases[db_index]
                        db_name = manage_database(db_name)
                        
                        if db_name is not None:
                            # If database still exists, ask if user wants to manage a collection
                            db_path = os.path.join(DB_DIR, db_name)
                            collections = [f.replace('.json', '') for f in os.listdir(db_path) if f.endswith('.json')]
                            
                            if collections:
                                print("\nCollections:")
                                for i, coll in enumerate(collections, 1):
                                    print(f"{i}. {coll}")
                                
                                try:
                                    coll_index = int(input("Enter collection number (0 to go back): ").strip()) - 1
                                    if coll_index == -1:
                                        continue
                                    if 0 <= coll_index < len(collections):
                                        collection_name = collections[coll_index]
                                        manage_collection(db_name, collection_name)
                                    else:
                                        print("Invalid collection number.")
                                except ValueError:
                                    print("Please enter a valid number.")
                            else:
                                print("No collections found in this database.")
                    else:
                        print("Invalid database number.")
                except ValueError:
                    print("Please enter a valid number.")
        
        elif choice == '3':
            # Open query editor
            query_editor()
        
        elif choice == '4':
            # Exit
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 