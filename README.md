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
    ├── checkpoints/     # Transaction checkpoints
    └── transaction_logs/ # Transaction logs
```

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

## Contributing

Feel free to submit issues and enhancement requests! 