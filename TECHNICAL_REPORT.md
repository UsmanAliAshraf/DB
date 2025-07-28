# MangoDB Technical Report
A detailed technical analysis of our document-based database system implementation.

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Core Components](#core-components)
3. [Transaction Management](#transaction-management)
4. [Concurrency Control](#concurrency-control)
5. [Data Storage and Persistence](#data-storage-and-persistence)
6. [Query Processing](#query-processing)
7. [Recovery System](#recovery-system)
8. [Limitations and Trade-offs](#limitations-and-trade-offs)

## System Architecture Overview

MangoDB is built as a layered architecture:

```
┌─────────────────┐
│   Web Interface │  Flask-based UI
├─────────────────┤
│  Query Parser   │  MongoDB-like syntax
├─────────────────┤
│ Transaction Mgr │  ACID & Concurrency
├─────────────────┤
│  Storage Layer  │  JSON files & Indexes
└─────────────────┘
```

## Core Components

### File Structure and Purpose

1. **app.py** - Main Application
   - Contains the Flask web server and `DocumentDB` class
   - Handles HTTP routes and request processing
   - Manages database operations (CRUD)
   - Coordinates between different components
   - Key classes:
     - `DocumentDB`: Main database class that orchestrates all operations
     - Routes: Handle HTTP endpoints for web interface

2. **document_validator.py** - Document Validation
   - Ensures document integrity and schema compliance
   - Manages unique constraints and indexing
   - Key classes:
     - `DocumentValidator`: Validates documents and enforces constraints

3. **query_parser.py** - Query Processing
   - Parses and validates database queries
   - Converts string queries to structured operations
   - Key functions:
     - `parse_raw_query`: Parses single queries
     - `parse_batch_queries`: Parses multiple queries

4. **indexing.py** - Index Management
   - Manages database indexes
   - Handles index creation, updates, and queries
   - Key classes:
     - `Index`: Represents a single index
     - `IndexManager`: Manages all indexes in a database

5. **bplus_tree.py** - Index Data Structure
   - Implements B+ tree for efficient indexing
   - Provides O(log n) operations for index lookups
   - Key classes:
     - `BPlusNode`: Node in the B+ tree
     - `BPlusTree`: Main B+ tree implementation

6. **transaction_manager.py** - Transaction Control
   - Manages ACID transactions
   - Handles concurrency control
   - Implements locking mechanism
   - Key classes:
     - `TransactionManager`: Manages transactions and locks

### Component Interactions

1. **Query Flow**:
   ```
   HTTP Request → app.py (route handler)
                  → query_parser.py (parse query)
                  → DocumentDB (process query)
                  → transaction_manager.py (begin transaction)
                  → document_validator.py (validate)
                  → indexing.py (update indexes)
                  → transaction_manager.py (commit)
   ```

2. **Document Insertion**:
   ```
   DocumentDB.insert()
   → TransactionManager.begin()
   → DocumentValidator.validate()
   → IndexManager.update_index()
   → TransactionManager.commit()
   ```

3. **Query Execution**:
   ```
   DocumentDB.execute_query()
   → QueryParser.parse()
   → TransactionManager.acquire_locks()
   → IndexManager.find_documents()
   → TransactionManager.release_locks()
   ```

4. **Index Management**:
   ```
   IndexManager.create_index()
   → BPlusTree.insert()
   → Index.save_to_disk()
   ```

### Data Flow

1. **Document Storage**:
   - Documents stored as JSON files
   - Each collection is a separate JSON file
   - Indexes stored in separate `.idx` files
   - Transaction logs in `transaction_logs/`

2. **Index Storage**:
   - B+ tree structure serialized to JSON
   - One index file per indexed field
   - Automatic index on `_id` field
   - Custom indexes on user-specified fields

3. **Transaction Logging**:
   - Operations logged before execution
   - Checkpoints for crash recovery
   - Log files in `transaction_logs/`
   - Checkpoint files in `checkpoints/`

### 1. Document Storage
**Concept**: Document-based storage allows flexible schema and nested data structures.

**Implementation**:
```python
class DocumentDB:
    def __init__(self):
        self.databases_dir = "databases/"
        self._ensure_databases_dir()
```

Each document is stored as a JSON object with a unique UUID:
```python
doc_id = str(uuid.uuid4())
document = {
    "_id": doc_id,
    "data": {...}
}
```

### 2. Transaction Management

#### ACID Properties Implementation

**Atomicity**:
- Each transaction is wrapped in a try-except block
- Operations are logged before execution
- Two-phase commit protocol:
  1. Prepare phase: Log operations
  2. Commit phase: Apply changes

```python
def execute_transaction(self, transaction_id):
    try:
        # Log operation
        self.log_operation(transaction_id, operation)
        # Execute operation
        result = self.execute_operation(operation)
        # Commit if successful
        self.commit_transaction(transaction_id)
        return result
    except Exception:
        self.abort_transaction(transaction_id)
        raise
```

**Consistency**:
Our system implements strong consistency through multiple mechanisms:

1. **Document Validation**:
   - Every document must have a unique `_id` field
   - Automatic UUID generation if not provided
   - Schema validation through JSON structure
   - Custom validation rules per collection

2. **Unique Indexing**:
   - Automatic indexing on `_id` field
   - Support for custom unique indexes
   - Index-based uniqueness enforcement
   - Efficient lookup using B+ tree structure

3. **Validation Flow**:
```
Document Insert/Update
        ↓
Check _id Field
        ↓
Validate Schema
        ↓
Check Unique Constraints
        ↓
Update Indexes
        ↓
Commit Changes
```

4. **Implementation Details**:
```python
class DocumentValidator:
    def validate_document(self, collection, document, is_update=False):
        # Ensure _id field
        document = self.ensure_id_field(document)
        
        # Check unique constraints
        for field, index in self.unique_indexes[collection].items():
            if not self._check_unique_constraint(field, document[field]):
                return False, "Duplicate value"
        
        return True, ""
```

5. **Index Management**:
   - Separate index files per field
   - Automatic index updates
   - Index cleanup on document deletion
   - Support for compound indexes

**Isolation Levels**:
```python
class IsolationLevel(Enum):
    READ_UNCOMMITTED = 1
    READ_COMMITTED = 2
    REPEATABLE_READ = 3
    SERIALIZABLE = 4
```

Implementation in `transaction_manager.py`:
```python
def begin_transaction(self, isolation_level):
    transaction_id = str(uuid.uuid4())
    self.transactions[transaction_id] = {
        "state": TransactionState.ACTIVE,
        "isolation_level": isolation_level,
        "locks": set()
    }
    return transaction_id
```

**Durability**:
- Transaction logging
- Periodic checkpointing
- Crash recovery mechanism

## Concurrency Control

### 1. Locking Mechanism

**Concept**: Document-level locking prevents concurrent modifications to the same document.

**Implementation Flow**:
```
Transaction Start
       ↓
Request Lock
       ↓
Check Lock Table
       ↓
Grant/Block Lock
       ↓
Operation Execution
       ↓
Release Lock
```

**Lock Types**:
```python
class LockType(Enum):
    READ = 1
    WRITE = 2
```

**Lock Manager Implementation**:
```python
class LockManager:
    def __init__(self):
        self.lock_table = {}  # doc_id -> {lock_type, transaction_id}

    def acquire_lock(self, doc_id, lock_type, transaction_id):
        if self._is_lock_compatible(doc_id, lock_type):
            self.lock_table[doc_id] = {
                "type": lock_type,
                "transaction_id": transaction_id
            }
            return True
        return False
```

### 2. Deadlock Detection

**Implementation**:
- Timeout-based approach
- Lock wait graph construction
- Cycle detection

```python
def detect_deadlock(self, transaction_id):
    wait_graph = self._build_wait_graph()
    if self._has_cycle(wait_graph):
        self._resolve_deadlock(transaction_id)
```

## Data Storage and Persistence

### 1. File Structure
```
databases/
├── db_name/
│   ├── collection.json
│   └── indexes/
│       └── field_name.idx
├── transaction_logs/
└── checkpoints/
```

### 2. Indexing System

**B+ Tree Implementation**:
```python
class BPlusTree:
    def __init__(self):
        self.root = None
        self.order = 4  # Maximum children per node

    def insert(self, key, value):
        if not self.root:
            self.root = LeafNode()
        return self._insert_recursive(self.root, key, value)
```

## Query Processing

### 1. Query Pipeline
```
Query String
    ↓
Parser (query_parser.py)
    ↓
Optimizer (queryOptimizer.py)
    ↓
Executor (queryProcessor.py)
    ↓
Result
```

### 2. Query Execution
```python
def execute_query(self, query):
    # Parse query
    operation, collection, params = parse_raw_query(query)
    
    # Start transaction
    transaction_id = self.begin_transaction()
    
    try:
        # Execute operation
        result = self._execute_operation(operation, collection, params)
        # Commit
        self.commit_transaction(transaction_id)
        return result
    except Exception:
        self.abort_transaction(transaction_id)
        raise
```

## Recovery System

### 1. Checkpointing
- Every 60 seconds
- Saves system state
- Maintains last 5 checkpoints

### 2. Log-Based Recovery
```python
def recover_from_crash(self):
    # Load latest checkpoint
    checkpoint = self._load_latest_checkpoint()
    
    # Replay logs
    logs = self._get_logs_after_checkpoint(checkpoint)
    for log in logs:
        if log["status"] == "committed":
            self._redo_operation(log)
        else:
            self._undo_operation(log)
```

## Limitations and Trade-offs

### Current Limitations
1. **Scalability**:
   - File-based storage limits concurrent access
   - No distributed architecture
   - Memory constraints for large datasets

2. **Performance**:
   - JSON parsing overhead
   - File I/O bottlenecks
   - Limited index types

3. **Features**:
   - No complex queries
   - Limited aggregation
   - Basic indexing only

### Design Decisions and Trade-offs

1. **Document-Level vs Collection-Level Locking**
   - Chose document-level for better concurrency
   - Trade-off: More complex lock management

2. **File-Based vs In-Memory Storage**
   - Chose file-based for durability
   - Trade-off: Slower performance

3. **B+ Tree Indexing**
   - Chose B+ tree for range queries
   - Trade-off: More complex implementation

## Future Improvements

1. **Performance**:
   - Implement caching
   - Add more index types
   - Optimize file I/O

2. **Features**:
   - Add complex queries
   - Implement aggregation
   - Support more data types

3. **Scalability**:
   - Add sharding
   - Implement replication
   - Support distributed architecture 