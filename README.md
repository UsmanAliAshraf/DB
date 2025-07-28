# MangoDB - Document-Based Database System

A lightweight, document-based database system with a modern web interface, inspired by MongoDB. This project implements a simple but powerful document database with transaction support and a user-friendly web interface.

## Features

### Core Database Features

- Document-based storage system
- JSON-based data format
- Transaction support with ACID properties
- Multiple isolation levels (READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE)
- Lock-based concurrency control
- Checkpoint and recovery system
- Transaction logging

### Web Interface Features

- Modern, dark-themed UI
- Database management (create, delete, list)
- Collection management (create, list)
- Interactive query editor
- Example queries for common operations
- Real-time query execution and results display

## Query Language

The system supports a MongoDB-like query syntax:

### Find Documents

```javascript
// Find all documents in a collection
db.collection.find()

// Find documents matching specific criteria
db.collection.find({"field": "value"})
```

### Insert Documents

```javascript
// Insert a new document
db.collection.insert({"name": "John", "age": 30})
```

### Update Documents

```javascript
// Update matching documents
db.collection.update({"name": "John"}, {"$set": {"age": 31}})
```

### Delete Documents

```javascript
// Delete matching documents
db.collection.delete({"name": "John"})
```

## Directory Structure

```
├── app.py                 # Main Flask application
├── transaction_manager.py # Transaction and lock management
├── query_parser.py       # Query parsing and execution
├── templates/            # HTML templates
│   ├── index.html       # Main page
│   ├── database.html    # Database view
│   └── query_editor.html # Query editor interface
└── databases/           # Database storage
    ├── checkpoints/     # Transaction checkpoints (DO NOT DELETE)
    └── transaction_logs/ # Transaction logs (DO NOT DELETE)
```

### Important Directories
1. **transaction_logs/**
   - Contains transaction history for each database
   - Essential for crash recovery and transaction tracking
   - Each database has its own log file (e.g., `dbname_transactions.log`)
   - **DO NOT DELETE** - Required for system operation

2. **checkpoints/**
   - Stores database state checkpoints
   - Used for transaction recovery
   - Maintains data consistency
   - **DO NOT DELETE** - Required for system operation

## Getting Started

1. Install the required dependencies:

```bash
pip install flask
```

2. Run the application:

```bash
python app.py
```

3. Open your browser and navigate to:

```
http://localhost:5000
```

## Usage

1. **Creating a Database**

   - Click the "+" button on the main page
   - Enter a database name (must start with a letter, can contain letters, numbers, and underscores)
2. **Creating a Collection**

   - Select a database
   - Click "Create Collection"
   - Enter a collection name
3. **Using the Query Editor**

   - Select a database and collection
   - Use the example queries or write your own
   - Click "Execute Query" to run

## Transaction Management

The system implements a robust transaction management system with:

- **Lock Manager**: Handles document-level locking
- **Transaction Manager**: Manages transaction states and checkpoints
- **Recovery System**: Recovers from crashes using checkpoints and logs

### Transaction Logs and Checkpoints
The system uses a combination of transaction logs and checkpoints for data durability and recovery:

1. **Transaction Logs** (`transaction_logs/`):
   - Records every database operation immediately
   - Contains detailed information about each transaction:
     ```json
     {
         "transaction_id": "282e1675-09a2-461a-91e4-0dcf3037995b",
         "timestamp": "2025-05-14T13:31:24.092697",
         "operation": "insert",
         "db_name": "example_db",
         "collection": "users",
         "document_id": "doc123",
         "before_state": null,
         "after_state": {"name": "John", "age": 30},
         "isolation_level": "serializable"
     }
     ```

2. **Checkpoints** (`checkpoints/`):
   - Created every 60 seconds automatically
   - Stores system state including active transactions
   - Keeps only the last 5 checkpoints to manage disk space
   - Example checkpoint:
     ```json
     {
         "timestamp": "2025-05-14T13:31:24.092697",
         "active_transactions": {
             "tid1": {
                 "state": "active",
                 "start_time": 1620997884.092697
             }
         },
         "last_checkpoint_time": 1620997884.092697
     }
     ```

3. **Log Cleanup**:
   - Old transaction logs are automatically cleaned up after checkpointing
   - Only logs after the last checkpoint are retained
   - Prevents unlimited growth of log files

### Query Processing Flow

When a query is executed, it follows this process:

1. **Client Request**:
   ```javascript
   db.users.insert({ name: "Usman", age: 20 })
   ```

2. **Query Parsing**:
   - Validates query syntax
   - Checks collection existence
   - Parses operation type and parameters

3. **Transaction Start**:
   - Creates new transaction with unique ID
   - Sets isolation level
   - Acquires necessary locks

4. **Transaction Logging**:
   - Immediately writes operation to transaction log
   - Records before and after states
   - Ensures durability

5. **Operation Execution**:
   - Performs the requested operation
   - Updates data in JSON files
   - Maintains data consistency

6. **Periodic Checkpointing**:
   - Every 60 seconds:
     - Creates system checkpoint
     - Cleans up old transaction logs
     - Maintains last 5 checkpoints

7. **Crash Recovery**:
   If system crashes:
   - Loads latest checkpoint
   - Replays transaction logs after checkpoint
   - Restores system to consistent state

### Example Flow:
```
Insert Query → Start Transaction → Log Operation → Execute → Commit
                    ↓
              Every 60 seconds
                    ↓
            Create Checkpoint → Cleanup Logs
```

## Contributing

Feel free to submit issues and enhancement requests!
