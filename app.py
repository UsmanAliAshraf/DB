from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import shutil
from query_parser import parse_raw_query, parse_batch_queries
from transaction_manager import TransactionManager, LockType, TransactionState, IsolationLevel
from indexing import IndexManager
from document_validator import DocumentValidator
import uuid
import time
app = Flask(__name__)

class DocumentDB:
    def __init__(self):
        self.databases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "databases")
        # Create all required directories first
        self._ensure_databases_dir()
        # Initialize transaction manager after directories are created
        self.transaction_manager = TransactionManager(self.databases_dir)
        # Initialize index manager
        self.index_managers = {}  # db_name -> IndexManager
        # Initialize document validator
        self.document_validators = {}  # db_name -> DocumentValidator
        self._recover_from_crash()
        self.max_batch_size = 100  # Maximum number of queries in a batch
        self.batch_timeout = 30  # Maximum time (seconds) for batch execution

    def _ensure_databases_dir(self):
        # Create all required directories with exist_ok=True
        os.makedirs(self.databases_dir, exist_ok=True)
        os.makedirs(os.path.join(self.databases_dir, "transaction_logs"), exist_ok=True)
        os.makedirs(os.path.join(self.databases_dir, "checkpoints"), exist_ok=True)
        # Create indexes directory for each existing database
        for db_name in self.list_databases():
            db_path = os.path.join(self.databases_dir, db_name)
            os.makedirs(os.path.join(db_path, "indexes"), exist_ok=True)

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
        # Exclude system directories from the list
        system_dirs = {'transaction_logs', 'checkpoints'}
        return [d for d in os.listdir(self.databases_dir) 
                if os.path.isdir(os.path.join(self.databases_dir, d)) 
                and d not in system_dirs]

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

    def _get_index_manager(self, db_name):
        """Get or create an index manager for a database"""
        if db_name not in self.index_managers:
            db_path = os.path.join(self.databases_dir, db_name)
            if os.path.exists(db_path):
                self.index_managers[db_name] = IndexManager(db_path)
        return self.index_managers.get(db_name)

    def _get_document_validator(self, db_name):
        """Get or create a document validator for a database"""
        if db_name not in self.document_validators:
            db_path = os.path.join(self.databases_dir, db_name)
            if os.path.exists(db_path):
                self.document_validators[db_name] = DocumentValidator(db_path)
                # Ensure _id field is always indexed
                for collection in self.list_collections(db_name):
                    self.document_validators[db_name].create_unique_index(collection, '_id')
        return self.document_validators.get(db_name)

    def create_index(self, db_name, collection_name, field_name):
        """Create an index on a collection field"""
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.SERIALIZABLE)
        
        try:
            # Validate names
            if not all([db_name, collection_name, field_name]):
                self.transaction_manager.abort_transaction(transaction_id)
                return False, "Database, collection, and field names are required"

            index_manager = self._get_index_manager(db_name)
            if not index_manager:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Database '{db_name}' does not exist"

            # Create the index
            if index_manager.create_index(collection_name, field_name):
                # Log the operation
                self.transaction_manager.log_operation(
                    transaction_id, 'create_index', db_name, collection_name, None,
                    None, {"field": field_name}
                )
                
                # Build the index with existing documents
                collection_path = os.path.join(self.databases_dir, db_name, f"{collection_name}.json")
                if os.path.exists(collection_path):
                    with open(collection_path, 'r') as f:
                        documents = json.load(f)
                        for doc in documents:
                            if field_name in doc:
                                index_manager.update_index(
                                    collection_name, field_name,
                                    doc[field_name], str(doc.get('_id', ''))
                                )
                
                # Commit transaction
                success, msg = self.transaction_manager.commit_transaction(transaction_id)
                if not success:
                    return False, f"Failed to commit transaction: {msg}"
                
                return True, f"Index created on {collection_name}.{field_name}"
            else:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Index already exists on {collection_name}.{field_name}"

        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return False, str(e)

    def drop_index(self, db_name, collection_name, field_name):
        """Drop an index from a collection field"""
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.SERIALIZABLE)
        
        try:
            index_manager = self._get_index_manager(db_name)
            if not index_manager:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Database '{db_name}' does not exist"

            if index_manager.drop_index(collection_name, field_name):
                # Log the operation
                self.transaction_manager.log_operation(
                    transaction_id, 'drop_index', db_name, collection_name, None,
                    {"field": field_name}, None
                )
                
                # Commit transaction
                success, msg = self.transaction_manager.commit_transaction(transaction_id)
                if not success:
                    return False, f"Failed to commit transaction: {msg}"
                
                return True, f"Index dropped from {collection_name}.{field_name}"
            else:
                self.transaction_manager.abort_transaction(transaction_id)
                return False, f"Index does not exist on {collection_name}.{field_name}"

        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return False, str(e)

    def list_indexes(self, db_name, collection_name):
        """List all indexes for a collection"""
        index_manager = self._get_index_manager(db_name)
        if not index_manager:
            return []
        return index_manager.list_indexes(collection_name)

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
                os.makedirs(os.path.join(db_path, "indexes"), exist_ok=True)
                # Initialize index manager for new database
                self.index_managers[db_name] = IndexManager(db_path)
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
                
                # Remove index manager for the database
                if db_name in self.index_managers:
                    del self.index_managers[db_name]
                
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
                
                # Initialize document validator and create _id index
                validator = self._get_document_validator(db_name)
                if validator:
                    validator.create_unique_index(collection_name, '_id')
                
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
        """Execute a single query"""
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.REPEATABLE_READ)
        
        try:
            operation, collection, params = parse_raw_query(query)
            if operation is None:
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": "Invalid query format"}
            
            # Get document validator
            validator = self._get_document_validator(db_name)
            if not validator:
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": f"Database '{db_name}' does not exist"}
            
            # Handle insert operations
            if operation in ['insert', 'insert_many']:
                collection_path = os.path.join(self.databases_dir, db_name, f"{collection}.json")
                if not os.path.exists(collection_path):
                    self.transaction_manager.abort_transaction(transaction_id)
                    return {"error": f"Collection '{collection}' does not exist"}
                
                try:
                    with open(collection_path, 'r') as f:
                        data = json.load(f)
                    
                    documents = params if operation == 'insert_many' else [params]
                    for doc in documents:
                        # Validate document
                        is_valid, message = validator.validate_document(collection, doc)
                        if not is_valid:
                            self.transaction_manager.abort_transaction(transaction_id)
                            return {"error": message}
                        
                        doc_id = doc['_id']
                        success, msg = self.transaction_manager.acquire_document_lock(
                            db_name, collection, doc_id, LockType.WRITE, transaction_id
                        )
                        if not success:
                            self.transaction_manager.abort_transaction(transaction_id)
                            return {"error": f"Failed to acquire write lock: {msg}"}
                        
                        self.transaction_manager.log_operation(
                            transaction_id, 'insert', db_name, collection, doc_id,
                            None, doc
                        )
                        data.append(doc)
                    
                    with open(collection_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    success, msg = self.transaction_manager.commit_transaction(transaction_id)
                    if not success:
                        return {"error": f"Failed to commit transaction: {msg}"}
                    
                    return {"message": f"Inserted {len(documents)} document(s) successfully!"}
                except Exception as e:
                    self.transaction_manager.abort_transaction(transaction_id)
                    return {"error": str(e)}
            
            # Handle update operations
            if operation == 'update':
                collection_path = os.path.join(self.databases_dir, db_name, f"{collection}.json")
                if not os.path.exists(collection_path):
                    self.transaction_manager.abort_transaction(transaction_id)
                    return {"error": f"Collection '{collection}' does not exist"}
                
                try:
                    with open(collection_path, 'r') as f:
                        data = json.load(f)
                    
                    docs_to_update = []
                    for doc in data:
                        if all(doc.get(k) == v for k, v in params['query'].items()):
                            # Validate updated document
                            updated_doc = {**doc, **params['update'].get('$set', {})}
                            is_valid, message = validator.validate_document(
                                collection, updated_doc, is_update=True, old_doc=doc
                            )
                            if not is_valid:
                                self.transaction_manager.abort_transaction(transaction_id)
                                return {"error": message}
                            
                            doc_id = doc['_id']
                            success, msg = self.transaction_manager.acquire_document_lock(
                                db_name, collection, doc_id, LockType.WRITE, transaction_id
                            )
                            if not success:
                                self.transaction_manager.abort_transaction(transaction_id)
                                return {"error": f"Failed to acquire write lock: {msg}"}
                            
                            self.transaction_manager.log_operation(
                                transaction_id, 'update', db_name, collection, doc_id,
                                doc, updated_doc
                            )
                            if '$set' in params['update']:
                                doc.update(params['update']['$set'])
                            docs_to_update.append(doc)
                    
                    with open(collection_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    success, msg = self.transaction_manager.commit_transaction(transaction_id)
                    if not success:
                        return {"error": f"Failed to commit transaction: {msg}"}
                    
                    return {"message": f"Updated {len(docs_to_update)} document(s)"}
                except Exception as e:
                    self.transaction_manager.abort_transaction(transaction_id)
                    return {"error": str(e)}
            
            # Handle other operations...
            # ... existing code for other operations ...

        except Exception as e:
            self.transaction_manager.abort_transaction(transaction_id)
            return {"error": str(e)}

    def execute_batch_query(self, db_name, queries_str):
        """Execute multiple queries in a single transaction (atomic, summary result)"""
        transaction_id = self.transaction_manager.begin_transaction(IsolationLevel.SERIALIZABLE)
        start_time = time.time()
        
        try:
            parsed_queries, error_info = parse_batch_queries(queries_str)
            if error_info is not None:
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": f"Query {error_info['index']} failed: {repr(error_info['query'])}\nsyntax error"}
            if not parsed_queries:
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": "Invalid query format"}
            
            if len(parsed_queries) > self.max_batch_size:
                self.transaction_manager.abort_transaction(transaction_id)
                return {"error": f"Batch size exceeds maximum limit of {self.max_batch_size}"}
            
            for idx, (operation, collection, params) in enumerate(parsed_queries):
                if time.time() - start_time > self.batch_timeout:
                    self.transaction_manager.abort_transaction(transaction_id)
                    return {"error": f"Batch execution timeout at query {idx+1}"}
                
                # Handle create_collection in batch
                if operation == 'create_collection':
                    success, message = self.create_collection(db_name, collection)
                    if not success:
                        self.transaction_manager.abort_transaction(transaction_id)
                        return {"error": f"Query {idx+1} failed: {message}"}
                    continue
                
                # Handle insert_many in batch
                if operation == 'insert_many':
                    collection_path = os.path.join(self.databases_dir, db_name, f"{collection}.json")
                    if not os.path.exists(collection_path):
                        self.transaction_manager.abort_transaction(transaction_id)
                        return {"error": f"Query {idx+1} failed: Collection '{collection}' does not exist"}
                    try:
                        with open(collection_path, 'r') as f:
                            data = json.load(f)
                        
                        # Get document validator
                        validator = self._get_document_validator(db_name)
                        if not validator:
                            self.transaction_manager.abort_transaction(transaction_id)
                            return {"error": f"Query {idx+1} failed: Database '{db_name}' does not exist"}
                        
                        for doc in params:
                            # Validate document and ensure _id field
                            is_valid, message = validator.validate_document(collection, doc)
                            if not is_valid:
                                self.transaction_manager.abort_transaction(transaction_id)
                                return {"error": f"Query {idx+1} failed: {message}"}
                            
                            doc_id = doc['_id']
                            success, msg = self.transaction_manager.acquire_document_lock(
                                db_name, collection, doc_id, LockType.WRITE, transaction_id
                            )
                            if not success:
                                self.transaction_manager.abort_transaction(transaction_id)
                                return {"error": f"Query {idx+1} failed: Failed to acquire write lock: {msg}"}
                            
                            self.transaction_manager.log_operation(
                                transaction_id, 'insert', db_name, collection, doc_id,
                                None, doc
                            )
                            data.append(doc)
                        
                        with open(collection_path, 'w') as f:
                            json.dump(data, f, indent=2)
                    except Exception as e:
                        self.transaction_manager.abort_transaction(transaction_id)
                        return {"error": f"Query {idx+1} failed: {str(e)}"}
                    continue
                
                collection_path = os.path.join(self.databases_dir, db_name, f"{collection}.json")
                if not os.path.exists(collection_path):
                    self.transaction_manager.abort_transaction(transaction_id)
                    return {"error": f"Query {idx+1} failed: Collection '{collection}' does not exist"}
                
                try:
                    with open(collection_path, 'r') as f:
                        data = json.load(f)
                    
                    if operation == 'find':
                        for doc in data:
                            if all(doc.get(k) == v for k, v in params.items()):
                                doc_id = str(doc.get('_id', id(doc)))
                                success, msg = self.transaction_manager.acquire_document_lock(
                                    db_name, collection, doc_id, LockType.READ, transaction_id
                                )
                                if not success:
                                    self.transaction_manager.abort_transaction(transaction_id)
                                    return {"error": f"Query {idx+1} failed: Failed to acquire read lock: {msg}"}
                    
                    elif operation == 'insert':
                        # Get document validator
                        validator = self._get_document_validator(db_name)
                        if not validator:
                            self.transaction_manager.abort_transaction(transaction_id)
                            return {"error": f"Query {idx+1} failed: Database '{db_name}' does not exist"}
                        
                        # Validate document and ensure _id field
                        is_valid, message = validator.validate_document(collection, params)
                        if not is_valid:
                            self.transaction_manager.abort_transaction(transaction_id)
                            return {"error": f"Query {idx+1} failed: {message}"}
                        
                        doc_id = params['_id']
                        success, msg = self.transaction_manager.acquire_document_lock(
                            db_name, collection, doc_id, LockType.WRITE, transaction_id
                        )
                        if not success:
                            self.transaction_manager.abort_transaction(transaction_id)
                            return {"error": f"Query {idx+1} failed: Failed to acquire write lock: {msg}"}
                        
                        self.transaction_manager.log_operation(
                            transaction_id, 'insert', db_name, collection, doc_id,
                            None, params
                        )
                        data.append(params)
                        with open(collection_path, 'w') as f:
                            json.dump(data, f, indent=2)
                    
                    elif operation == 'update':
                        for doc in data:
                            if all(doc.get(k) == v for k, v in params['query'].items()):
                                doc_id = str(doc.get('_id', id(doc)))
                                success, msg = self.transaction_manager.acquire_document_lock(
                                    db_name, collection, doc_id, LockType.WRITE, transaction_id
                                )
                                if not success:
                                    self.transaction_manager.abort_transaction(transaction_id)
                                    return {"error": f"Query {idx+1} failed: Failed to acquire write lock: {msg}"}
                                self.transaction_manager.log_operation(
                                    transaction_id, 'update', db_name, collection, doc_id,
                                    doc, {**doc, **params['update']}
                                )
                                if '$set' in params['update']:
                                    doc.update(params['update']['$set'])
                        with open(collection_path, 'w') as f:
                            json.dump(data, f, indent=2)
                    
                    elif operation == 'delete':
                        docs_to_delete = []
                        for doc in data:
                            if all(doc.get(k) == v for k, v in params.items()):
                                doc_id = str(doc.get('_id', id(doc)))
                                success, msg = self.transaction_manager.acquire_document_lock(
                                    db_name, collection, doc_id, LockType.WRITE, transaction_id
                                )
                                if not success:
                                    self.transaction_manager.abort_transaction(transaction_id)
                                    return {"error": f"Query {idx+1} failed: Failed to acquire write lock: {msg}"}
                                self.transaction_manager.log_operation(
                                    transaction_id, 'delete', db_name, collection, doc_id,
                                    doc, None
                                )
                                docs_to_delete.append(doc)
                        data = [doc for doc in data if doc not in docs_to_delete]
                        with open(collection_path, 'w') as f:
                            json.dump(data, f, indent=2)
                except Exception as e:
                    self.transaction_manager.abort_transaction(transaction_id)
                    return {"error": f"Query {idx+1} failed: {str(e)}"}
            success, msg = self.transaction_manager.commit_transaction(transaction_id)
            if not success:
                return {"error": f"Failed to commit transaction: {msg}"}
            return {"message": f"All {len(parsed_queries)} queries executed successfully!"}
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
    
    # Check if query contains semicolons (batch query)
    if ';' in query:
        result = db.execute_batch_query(db_name, query)
    else:
        result = db.execute_query(db_name, query)
    
    return jsonify(result)

@app.route('/create_index/<db_name>/<collection_name>', methods=['POST'])
def create_index(db_name, collection_name):
    field_name = request.form.get('field_name')
    if not field_name:
        return jsonify({"success": False, "message": "Field name is required"})
    
    success, message = db.create_index(db_name, collection_name, field_name)
    return jsonify({"success": success, "message": message})

@app.route('/drop_index/<db_name>/<collection_name>', methods=['POST'])
def drop_index(db_name, collection_name):
    field_name = request.form.get('field_name')
    success, message = db.drop_index(db_name, collection_name, field_name)
    return jsonify({"success": success, "message": message})

@app.route('/list_indexes/<db_name>/<collection_name>')
def list_indexes(db_name, collection_name):
    indexes = db.list_indexes(db_name, collection_name)
    return jsonify({"indexes": indexes})

if __name__ == '__main__':
    app.run(debug=True)