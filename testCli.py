import os
import json
from query_parser import parse_raw_query

class DocumentDB:
    def __init__(self):
        self.current_db = None
        self.databases_dir = "databases"
        self._ensure_databases_dir()

    def _ensure_databases_dir(self):
        if not os.path.exists(self.databases_dir):
            os.makedirs(self.databases_dir)

    def list_databases(self):
        if not os.path.exists(self.databases_dir):
            return []
        return [d for d in os.listdir(self.databases_dir) 
                if os.path.isdir(os.path.join(self.databases_dir, d))]

    def create_database(self, db_name):
        db_path = os.path.join(self.databases_dir, db_name)
        if os.path.exists(db_path):
            return False, f"Database '{db_name}' already exists"
        os.makedirs(db_path)
        return True, f"Database '{db_name}' created successfully"

    def use_database(self, db_name):
        db_path = os.path.join(self.databases_dir, db_name)
        if not os.path.exists(db_path):
            return False, f"Database '{db_name}' does not exist"
        self.current_db = db_name
        return True, f"Using database '{db_name}'"

    def list_collections(self):
        if not self.current_db:
            return []
        db_path = os.path.join(self.databases_dir, self.current_db)
        return [f.replace('.json', '') for f in os.listdir(db_path) 
                if f.endswith('.json')]

    def create_collection(self, collection_name):
        if not self.current_db:
            return False, "No database selected"
        
        collection_path = os.path.join(self.databases_dir, self.current_db, f"{collection_name}.json")
        if os.path.exists(collection_path):
            return False, f"Collection '{collection_name}' already exists"
        
        with open(collection_path, 'w') as f:
            json.dump([], f)
        return True, f"Collection '{collection_name}' created successfully"

    def execute_query(self, query):
        if not self.current_db:
            return "❌ No database selected. Use 'use' command first."
        
        operation, collection, params = parse_raw_query(query)
        if operation is None:
            return "❌ Invalid query format"
        
        collection_path = os.path.join(self.databases_dir, self.current_db, f"{collection}.json")
        if not os.path.exists(collection_path):
            return f"❌ Collection '{collection}' does not exist"

        try:
            with open(collection_path, 'r') as f:
                data = json.load(f)

            if operation == 'find':
                # Simple find implementation
                if not params:
                    return data
                results = []
                for doc in data:
                    if all(doc.get(k) == v for k, v in params.items()):
                        results.append(doc)
                return results

            elif operation == 'insert':
                data.append(params)
                with open(collection_path, 'w') as f:
                    json.dump(data, f, indent=2)
                return f"✅ Document inserted successfully"

            elif operation == 'update':
                query_params = params['query']
                update_params = params['update']
                updated = 0
                for doc in data:
                    if all(doc.get(k) == v for k, v in query_params.items()):
                        if '$set' in update_params:
                            doc.update(update_params['$set'])
                        updated += 1
                with open(collection_path, 'w') as f:
                    json.dump(data, f, indent=2)
                return f"✅ Updated {updated} document(s)"

            elif operation == 'delete':
                query_params = params
                data = [doc for doc in data if not all(doc.get(k) == v for k, v in query_params.items())]
                with open(collection_path, 'w') as f:
                    json.dump(data, f, indent=2)
                return f"✅ Documents deleted successfully"

        except Exception as e:
            return f"❌ Error executing query: {str(e)}"

def print_menu():
    print("\n📦 DocumentDB CLI Menu")
    print("1. List Databases")
    print("2. Create Database")
    print("3. Use Database")
    print("4. List Collections")
    print("5. Create Collection")
    print("6. Query Editor")
    print("7. Exit")
    print("\nCurrent Database:", db.current_db if db.current_db else "None")

def query_editor():
    print("\n📝 Query Editor")
    print("Type your queries in MongoDB format:")
    print("→ db.collection.insert({\"field\": \"value\"})")
    print("→ db.collection.find({\"field\": \"value\"})")
    print("→ db.collection.update({\"field\": \"value\"}, {\"$set\": {\"field\": \"new_value\"}})")
    print("→ db.collection.delete({\"field\": \"value\"})")
    print("Type 'back' to return to main menu\n")

    while True:
        user_input = input(">>> ").strip()
        if user_input.lower() == 'back':
            break
        
        result = db.execute_query(user_input)
        print(result)

def main():
    global db
    db = DocumentDB()

    while True:
        print_menu()
        choice = input("\nEnter your choice (1-7): ").strip()

        if choice == '1':
            databases = db.list_databases()
            if databases:
                print("\nAvailable Databases:")
                for db_name in databases:
                    print(f"→ {db_name}")
            else:
                print("\nNo databases found")

        elif choice == '2':
            db_name = input("Enter database name: ").strip()
            success, message = db.create_database(db_name)
            print(f"\n{message}")

        elif choice == '3':
            db_name = input("Enter database name: ").strip()
            success, message = db.use_database(db_name)
            print(f"\n{message}")

        elif choice == '4':
            collections = db.list_collections()
            if collections:
                print("\nCollections in current database:")
                for collection in collections:
                    print(f"→ {collection}")
            else:
                print("\nNo collections found")

        elif choice == '5':
            if not db.current_db:
                print("\n❌ No database selected. Use 'use' command first.")
                continue
            collection_name = input("Enter collection name: ").strip()
            success, message = db.create_collection(collection_name)
            print(f"\n{message}")

        elif choice == '6':
            if not db.current_db:
                print("\n❌ No database selected. Use 'use' command first.")
                continue
            query_editor()

        elif choice == '7':
            print("\n👋 Thank you for using DocumentDB CLI. Goodbye!")
            break

        else:
            print("\n❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
