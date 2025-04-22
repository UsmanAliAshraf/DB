from db import MyDB
import json
import os
import shutil

from query_parser import parse_raw_query, format_query_examples

DB_DIR = "data"

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def print_main_menu():
    print("\n=== Welcome to Document Based DB ===")
    print("1. Create New Database")
    print("2. View Existing Databases")
    print("3. Open Query Editor")
    print("4. Exit")
    print("=======================")

def print_database_menu(db_name):
    print(f"\n=== Database: {db_name} ===")
    print("1. View Collections")
    print("2. Create New Collection")
    print("3. Rename Database")
    print("4. Delete Database")
    print("5. Back to Main Menu")
    print("=======================")

def print_collection_menu(db_name, collection_name):
    print(f"\n=== Collection: {collection_name} in {db_name} ===")
    print("1. Insert Document")
    print("2. Find Documents")
    print("3. Update Document")
    print("4. Delete Document")
    print("5. Show All Documents")
    print("6. Back to Database Menu")
    print("=========================")

def print_query_editor_menu():
    print("\n=== Query Editor ===")
    print("1. Select Database")
    print("2. Write Raw Query")
    print("3. Back to Main Menu")
    print("===================")

def get_database_name():
    return input("Enter database name: ").strip()

def get_collection_name():
    return input("Enter collection name: ").strip()

def list_databases():
    databases = [d for d in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, d))]
    if databases:
        print("\nExisting Databases:")
        for i, db in enumerate(databases, 1):
            print(f"{i}. {db}")
    else:
        print("\nNo databases found.")
    return databases

def create_database():
    db_name = get_database_name()
    db_path = os.path.join(DB_DIR, db_name)

    if os.path.exists(db_path):
        print(f"Database '{db_name}' already exists.")
        return None

    os.makedirs(db_path)
    print(f"Database '{db_name}' created successfully.")

    if input("Do you want to create a collection in this database? (yes/no): ").strip().lower() == 'yes':
        collection_name = get_collection_name()
        with open(os.path.join(db_path, f"{collection_name}.json"), 'w') as f:
            json.dump([], f)
        print(f"Collection '{collection_name}' created successfully.")
    return db_name

def manage_database(db_name):
    db_path = os.path.join(DB_DIR, db_name)
    while True:
        print_database_menu(db_name)
        choice = input("Enter your choice (1-5): ").strip()

        if choice == '1':
            collections = [f.replace('.json', '') for f in os.listdir(db_path) if f.endswith('.json')]
            if collections:
                print("\nCollections:")
                for i, coll in enumerate(collections, 1):
                    print(f"{i}. {coll}")
            else:
                print("\nNo collections found in this database.")

        elif choice == '2':
            collection_name = get_collection_name()
            collection_path = os.path.join(db_path, f"{collection_name}.json")
            if os.path.exists(collection_path):
                print(f"Collection '{collection_name}' already exists.")
            else:
                with open(collection_path, 'w') as f:
                    json.dump([], f)
                print(f"Collection '{collection_name}' created successfully.")

        elif choice == '3':
            new_name = input("Enter new database name: ").strip()
            new_path = os.path.join(DB_DIR, new_name)
            if os.path.exists(new_path):
                print(f"Database '{new_name}' already exists.")
            else:
                os.rename(db_path, new_path)
                print(f"Database renamed from '{db_name}' to '{new_name}'.")
                return new_name

        elif choice == '4':
            if input(f"Are you sure you want to delete database '{db_name}'? (yes/no): ").strip().lower() == 'yes':
                shutil.rmtree(db_path)
                print(f"Database '{db_name}' deleted successfully.")
                return None
            else:
                print("Deletion cancelled.")

        elif choice == '5':
            return db_name
        else:
            print("Invalid choice. Please try again.")

def manage_collection(db_name, collection_name):
    db = MyDB(db_name, collection_name)
    while True:
        print_collection_menu(db_name, collection_name)
        choice = input("Enter your choice (1-6): ").strip()

        if choice == '1':
            try:
                doc = json.loads(input("Enter document (in JSON format): "))
                db.insert(doc)
                print("Document inserted successfully!")
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == '2':
            try:
                query = json.loads(input("Enter query (in JSON format): "))
                results = db.find(query)
                print("\nFound documents:")
                for doc in results:
                    print(json.dumps(doc, indent=2))
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == '3':
            try:
                query = json.loads(input("Enter query (in JSON format): "))
                update_values = json.loads(input("Enter update values (in JSON format): "))
                db.update(query, update_values)
                print("Documents updated successfully!")
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == '4':
            try:
                query = json.loads(input("Enter query (in JSON format): "))
                matches = db.find(query)
                if matches:
                    print("\nDocuments to be deleted:")
                    for doc in matches:
                        print(json.dumps(doc, indent=2))
                    if input("Confirm deletion? (yes/no): ").lower() == 'yes':
                        db.delete(query)
                        print("Documents deleted successfully!")
                else:
                    print("No matching documents found.")
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == '5':
            try:
                results = db.find({})
                for doc in results:
                    print(json.dumps(doc, indent=2))
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == '6':
            break
        else:
            print("Invalid choice. Please try again.")

def execute_raw_query(db_name, query_str):
    operation, collection_name, params = parse_raw_query(query_str)
    if not operation:
        print("Error: Invalid query format.")
        print(format_query_examples())
        return

    collection_path = os.path.join(DB_DIR, db_name, f"{collection_name}.json")
    if not os.path.exists(collection_path):
        print(f"Collection '{collection_name}' does not exist in database '{db_name}'.")
        return

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
            matches = db.find(params)
            if matches:
                print("\nDocuments to be deleted:")
                for doc in matches:
                    print(json.dumps(doc, indent=2))
                if input("Confirm deletion? (yes/no): ").lower() == 'yes':
                    db.delete(params)
                    print("Documents deleted successfully!")
    except Exception as e:
        print(f"Error executing query: {str(e)}")

def query_editor():
    db_name = None
    while True:
        print_query_editor_menu()
        choice = input("Enter your choice (1-3): ").strip()

        if choice == '1':
            databases = list_databases()
            if databases:
                try:
                    db_index = int(input("Enter database number: ")) - 1
                    if 0 <= db_index < len(databases):
                        db_name = databases[db_index]
                        print(f"Selected database: {db_name}")
                        collections = [f.replace('.json', '') for f in os.listdir(os.path.join(DB_DIR, db_name)) if f.endswith('.json')]
                        print("\nCollections:")
                        for coll in collections:
                            print(f"- {coll}")
                except Exception:
                    print("Invalid input.")

        elif choice == '2':
            if db_name:
                print("\n=== Raw Query Editor ===")
                print("Examples:")
                print(format_query_examples())
                query_str = input("> ")
                if query_str.lower() != 'exit':
                    execute_raw_query(db_name, query_str)
            else:
                print("Please select a database first.")

        elif choice == '3':
            break
        else:
            print("Invalid choice.")

def main():
    while True:
        print_main_menu()
        choice = input("Enter your choice (1-4): ").strip()

        if choice == '1':
            create_database()
        elif choice == '2':
            databases = list_databases()
            if databases:
                try:
                    db_index = int(input("Enter database number (0 to go back): ")) - 1
                    if db_index == -1:
                        continue
                    if 0 <= db_index < len(databases):
                        db_name = manage_database(databases[db_index])
                        if db_name:
                            collections = [f.replace('.json', '') for f in os.listdir(os.path.join(DB_DIR, db_name)) if f.endswith('.json')]
                            if collections:
                                for i, coll in enumerate(collections, 1):
                                    print(f"{i}. {coll}")
                                try:
                                    coll_index = int(input("Enter collection number (0 to go back): ")) - 1
                                    if coll_index == -1:
                                        continue
                                    if 0 <= coll_index < len(collections):
                                        manage_collection(db_name, collections[coll_index])
                                except ValueError:
                                    print("Invalid number.")
                except ValueError:
                    print("Invalid input.")
        elif choice == '3':
            query_editor()
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
