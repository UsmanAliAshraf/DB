from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import shutil
from query_parser import parse_raw_query
from transaction_manager import TransactionManager, LockType, TransactionState, IsolationLevel
import uuid
import time

app = Flask(__name__)

class DocumentDB:
    def __init__(self):
        self.databases_dir = "databases"
        # Create all required directories first
        self._ensure_databases_dir()
        # Initialize transaction manager after directories are created
        self.transaction_manager = TransactionManager(self.databases_dir)
        self._recover_from_crash()

    def _ensure_databases_dir(self):
        # Create all required directories with exist_ok=True
        os.makedirs(self.databases_dir, exist_ok=True)
        os.makedirs(os.path.join(self.databases_dir, "transaction_logs"), exist_ok=True)
        os.makedirs(os.path.join(self.databases_dir, "checkpoints"), exist_ok=True)

    def _recover_from_crash(self):
        """Recover the system state after a crash"""
        # First ensure all required directories exist
        self._ensure_databases_dir()
        
        # Try to recover from checkpoint
        success, message = self.transaction_manager.recover_from_checkpoint()
        if not success:
            print(f"Recovery failed: {message}")
            # Just ensure directories exist, don't delete anything
            self._ensure_databases_dir()

    def list_databases(self):
        if not os.path.exists(self.databases_dir):
            return []
        return [d for d in os.listdir(self.databases_dir) 
                if os.path.isdir(os.path.join(self.databases_dir, d))]

    def validate_name(self, name, type_name):
        """Validate database or collection name"""
        if not name:
            return False, f"{type_name} name cannot be empty"
        
        # Check if starts with letter
        if not name[0].isalpha():
            return False, f"{type_name} name must start with a letter"
        
        # Check if contains only allowed characters
        if not all(c.isalnum() or c == '_' for c in name):
            return False, f"{type_name} name can only contain letters, numbers, and underscores"
        
        return True, ""

    def create_database(self, db_name):
        """Create a new database"""
        # Start transaction
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.SERIALIZABLE)
        
        try:
            # Validate database name
            is_valid, message = self.validate_name(db_name, "Database")
            if not is_valid:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, message

            db_path = os.path.join(self.databases_dir, db_name)
            if os.path.exists(db_path):
                self.transaction_manager.abort_transaction(transaction_id)
                return False, "Database already exists"
            
            try:
                os.makedirs(db_path)
                # Log the operation
                self.transaction_manager.log_operation(
                    transaction_id, 'create_database', db_name, None, None,
                    None, {"name": db_name}
                )
                
                # Commit transaction
                success, msg = self.transaction_manager.commit_transaction(transaction_id)
                if not success:
                    return False, f"Failed to commit transaction: {msg}"
                
                return True, "Database created successfully"
            except Exception as e:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Error creating database: {str(e)}"
        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return False, str(e)

    def delete_database(self, db_name):
        # Start transaction
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.SERIALIZABLE)
        
        try:
            db_path = os.path.join(self.databases_dir, db_name)
            if not os.path.exists(db_path):
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Database '{db_name}' does not exist"
            
            try:
                # Log the operation before deletion
                self.transaction_manager.log_operation(
                    transaction_id, 'delete_database', db_name, None, None,
                    {"path": db_path}, None
                )
                
                shutil.rmtree(db_path)
                
                # Commit transaction
                success, msg = self.transaction_manager.commit_transaction(transaction_id)
                if not success:
                    return False, f"Failed to commit transaction: {msg}"
                
                return True, f"Database '{db_name}' deleted successfully"
            except Exception as e:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Error deleting database: {str(e)}"
        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return False, str(e)

    def list_collections(self, db_name):
        # Start transaction
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.READ_COMMITTED)
        
        try:
            db_path = os.path.join(self.databases_dir, db_name)
            if not os.path.exists(db_path):
                self.transaction_manager.abort_transaction(transaction_id)
                return []
            
            collections = [f.replace('.json', '') for f in os.listdir(db_path) 
                         if f.endswith('.json')]
            
            # Commit transaction
            self.transaction_manager.commit_transaction(transaction_id)
            return collections
        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return []

    def create_collection(self, db_name, collection_name):
        """Create a new collection in the specified database"""
        # Start transaction
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.SERIALIZABLE)
        
        try:
            # Validate collection name
            is_valid, message = self.validate_name(collection_name, "Collection")
            if not is_valid:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, message

            db_path = os.path.join(self.databases_dir, db_name)
            if not os.path.exists(db_path):
                self.transaction_manager.abort_transaction(transaction_id)
                return False, "Database does not exist"
            
            collection_path = os.path.join(db_path, f"{collection_name}.json")
            if os.path.exists(collection_path):
                self.transaction_manager.abort_transaction(transaction_id)
                return False, "Collection already exists"
            
            try:
                with open(collection_path, 'w') as f:
                    json.dump([], f)
                
                # Log the operation
                self.transaction_manager.log_operation(
                    transaction_id, 'create_collection', db_name, collection_name, None,
                    None, {"name": collection_name}
                )
                
                # Commit transaction
                success, msg = self.transaction_manager.commit_transaction(transaction_id)
                if not success:
                    return False, f"Failed to commit transaction: {msg}"
                
                return True, "Collection created successfully"
            except Exception as e:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Error creating collection: {str(e)}"
        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return False, str(e)

    def execute_query(self, db_name, query):
        # Start a new transaction with appropriate isolation level
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.REPEATABLE_READ)
        
        try:
            operation, collection, params = parse_raw_query(query)
            if operation is None:
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": "Invalid query format"}
            
            collection_path = os.path.join(self.databases_dir, db_name, f"{collection}.json")
            if not os.path.exists(collection_path):
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": f"Collection '{collection}' does not exist"}

            try:
                with open(collection_path, 'r') as f:
                    data = json.load(f)

                if operation == 'find':
                    # For read operations, acquire read locks on all documents
                    for doc in data:
                        doc_id = str(doc.get('_id', id(doc)))
                        success, msg = self.transaction_manager.acquire_document_lock(
                            db_name, collection, doc_id, LockType.READ, transaction_id
                        )
                        if not success:
                            self.transaction_manager.abort_transaction(transaction_id)
                            return {"error": f"Failed to acquire read lock: {msg}"}

                    if not params:
                        result = {"data": data}
                    else:
                        results = []
                        for doc in data:
                            if all(doc.get(k) == v for k, v in params.items()):
                                results.append(doc)
                        result = {"data": results}

                elif operation == 'insert':
                    # For insert, we need a write lock on the collection
                    doc_id = str(uuid.uuid4())
                    success, msg = self.transaction_manager.acquire_document_lock(
                        db_name, collection, doc_id, LockType.WRITE, transaction_id
                    )
                    if not success:
                        self.transaction_manager.abort_transaction(transaction_id)
                        return {"error": f"Failed to acquire write lock: {msg}"}

                    # Log the operation
                    self.transaction_manager.log_operation(
                        transaction_id, 'insert', db_name, collection, doc_id,
                        None, params
                    )

                    data.append(params)
                    with open(collection_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    result = {"message": "Document inserted successfully"}

                elif operation == 'update':
                    # For update, we need write locks on matching documents
                    updated = 0
                    for doc in data:
                        if all(doc.get(k) == v for k, v in params['query'].items()):
                            doc_id = str(doc.get('_id', id(doc)))
                            success, msg = self.transaction_manager.acquire_document_lock(
                                db_name, collection, doc_id, LockType.WRITE, transaction_id
                            )
                            if not success:
                                self.transaction_manager.abort_transaction(transaction_id)
                                return {"error": f"Failed to acquire write lock: {msg}"}

                            # Log the operation
                            before_state = doc.copy()
                            if '$set' in params['update']:
                                doc.update(params['update']['$set'])
                            after_state = doc
                            self.transaction_manager.log_operation(
                                transaction_id, 'update', db_name, collection, doc_id,
                                before_state, after_state
                            )
                            updated += 1

                    with open(collection_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    result = {"message": f"Updated {updated} document(s)"}

                elif operation == 'delete':
                    # For delete, we need write locks on matching documents
                    docs_to_delete = []
                    for doc in data:
                        if all(doc.get(k) == v for k, v in params.items()):
                            doc_id = str(doc.get('_id', id(doc)))
                            success, msg = self.transaction_manager.acquire_document_lock(
                                db_name, collection, doc_id, LockType.WRITE, transaction_id
                            )
                            if not success:
                                self.transaction_manager.abort_transaction(transaction_id)
                                return {"error": f"Failed to acquire write lock: {msg}"}

                            # Log the operation
                            self.transaction_manager.log_operation(
                                transaction_id, 'delete', db_name, collection, doc_id,
                                doc, None
                            )
                            docs_to_delete.append(doc)

                    data = [doc for doc in data if doc not in docs_to_delete]
                    with open(collection_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    result = {"message": "Documents deleted successfully"}

                # Commit the transaction
                success, msg = self.transaction_manager.commit_transaction(transaction_id)
                if not success:
                    return {"error": f"Failed to commit transaction: {msg}"}

                return result

            except Exception as e:
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": str(e)}

        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return {"error": str(e)}

db = DocumentDB()

@app.route('/')
def index():
    databases = db.list_databases()
    return render_template('index.html', databases=databases)

@app.route('/create_database', methods=['POST'])
def create_database():
    db_name = request.form.get('db_name')
    success, message = db.create_database(db_name)
    return jsonify({"success": success, "message": message})

@app.route('/delete_database', methods=['POST'])
def delete_database():
    db_name = request.form.get('db_name')
    success, message = db.delete_database(db_name)
    return jsonify({"success": success, "message": message})

@app.route('/database/<db_name>')
def view_database(db_name):
    collections = db.list_collections(db_name)
    return render_template('database.html', db_name=db_name, collections=collections)

@app.route('/create_collection/<db_name>', methods=['POST'])
def create_collection(db_name):
    collection_name = request.form.get('collection_name')
    if not collection_name:
        return jsonify({"success": False, "message": "Collection name is required"})
    
    success, message = db.create_collection(db_name, collection_name)
    return jsonify({"success": success, "message": message})

@app.route('/query_editor')
@app.route('/query_editor/<db_name>')
def query_editor(db_name):
    collections = db.list_collections(db_name)
    return render_template('query_editor.html', db_name=db_name, collections=collections)

@app.route('/execute_query', methods=['POST'])
def execute_query():
    db_name = request.form.get('db_name')
    query = request.form.get('query')
    result = db.execute_query(db_name, query)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True) 