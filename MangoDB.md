# MangoDB Project Documentation

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Core Components](#2-core-components)
3. [ACID Properties Implementation](#3-acid-properties-implementation)
4. [Key Features](#4-key-features)
5. [Technical Implementation](#5-technical-implementation)
6. [Future Enhancements](#6-future-enhancements)

## 1. Project Overview
MangoDB is a document-oriented database system with a web interface that implements ACID properties. It provides MongoDB-style querying capabilities with transaction support, ensuring data consistency and reliability.

### 1.1 Purpose
- Provide a lightweight, ACID-compliant document database
- Support MongoDB-style querying
- Ensure data consistency and reliability
- Handle concurrent operations safely

### 1.2 Key Features
- Document-level transaction support
- MongoDB-style query interface
- Web-based management interface
- ACID compliance
- Concurrent operation handling

## 2. Core Components

### 2.1 DocumentDB Class
The main database management class that handles:
- Database and collection operations
- Transaction management
- Data persistence
- Query execution

### 2.2 Transaction Manager
Manages all transaction-related operations:
- Transaction lifecycle
- Lock management
- Transaction logging
- Recovery procedures

### 2.3 Lock Manager
Handles concurrency control:
- Document-level locking
- Lock acquisition and release
- Deadlock detection
- Lock timeout management

## 3. ACID Properties Implementation

### 3.1 Atomicity
Ensures that all operations in a transaction are completed successfully or none are.

#### Implementation Details:
1. **Transaction Wrapping**
   - Every operation is wrapped in a transaction
   - Operations include: create, read, update, delete (CRUD)
   - Each transaction has a unique ID

2. **Transaction States**
   ```python
   class TransactionState(Enum):
       ACTIVE = "active"
       COMMITTED = "committed"
       ABORTED = "aborted"
       BLOCKED = "blocked"
   ```

3. **Atomic Operations**
   - All operations in a transaction either:
     - Complete successfully (commit)
     - Fail completely (abort)
   - No partial operations allowed

4. **Rollback Mechanism**
   - Automatic rollback on failure
   - State restoration using logs
   - Cleanup of partial changes

### 3.2 Consistency
Ensures that the database remains in a valid state before and after transactions.

#### Implementation Details:
1. **Data Validation**
   - Database name validation
   - Collection name validation
   - Document structure validation

2. **State Management**
   - Pre-operation state tracking
   - Post-operation state verification
   - Constraint checking

3. **Lock-based Consistency**
   - Document-level locking
   - Prevents concurrent modifications
   - Ensures data integrity

### 3.3 Isolation
Ensures that concurrent transactions do not interfere with each other.

#### Implementation Details:
1. **Isolation Levels**
   ```python
   class IsolationLevel(Enum):
       READ_UNCOMMITTED = "read_uncommitted"
       READ_COMMITTED = "read_committed"
       REPEATABLE_READ = "repeatable_read"
       SERIALIZABLE = "serializable"
   ```

2. **Lock Types**
   ```python
   class LockType(Enum):
       READ = "read"
       WRITE = "write"
   ```

3. **Deadlock Detection**
   - Wait-for graph implementation
   - Cycle detection
   - Automatic deadlock resolution

4. **Lock Management**
   - Document-level granularity
   - Lock timeout mechanism
   - Lock escalation
   - Lock waiting queue

### 3.4 Durability
Ensures that committed transactions persist even after system failure.

#### Implementation Details:
1. **Transaction Logging**
   - Operation logging
   - State tracking
   - Timestamp recording
   - Before/after states

2. **Checkpoint Mechanism**
   - Regular state checkpoints
   - Checkpoint file management
   - State persistence

3. **Recovery System**
   - Crash recovery
   - Log replay
   - State restoration
   - Checkpoint-based recovery

## 4. Key Features

### 4.1 Transaction Management
1. **Transaction Lifecycle**
   - Begin transaction
   - Acquire locks
   - Execute operations
   - Commit/abort
   - Release locks

2. **Lock Management**
   - Document-level locking
   - Lock timeout (30 seconds default)
   - Lock waiting queue
   - Deadlock detection

3. **Recovery System**
   - Checkpoint creation
   - Log replay
   - State restoration
   - Crash recovery

### 4.2 Concurrency Control
1. **Lock Types**
   - Read locks (shared)
   - Write locks (exclusive)
   - Lock escalation
   - Lock timeout

2. **Deadlock Handling**
   - Wait-for graph
   - Cycle detection
   - Automatic resolution
   - Transaction abort

### 4.3 Data Operations
1. **CRUD Operations**
   - Create: Document insertion
   - Read: Document querying
   - Update: Document modification
   - Delete: Document removal

2. **Query Processing**
   - MongoDB-style queries
   - Document filtering
   - Result aggregation
   - Error handling

## 5. Technical Implementation

### 5.1 File Structure
```
MangoDB/
├── app.py                 # Main application file
├── transaction_manager.py # Transaction management
├── query_parser.py       # Query parsing and processing
├── databases/           # Database storage
├── transaction_logs/    # Transaction logs
└── checkpoints/        # System checkpoints
```

### 5.2 Key Classes
1. **DocumentDB**
   - Database management
   - Collection operations
   - Query execution
   - Transaction handling

2. **TransactionManager**
   - Transaction control
   - Lock management
   - Log management
   - Recovery handling

3. **LockManager**
   - Lock acquisition
   - Lock release
   - Deadlock detection
   - Lock timeout

## 6. Future Enhancements

### 6.1 Performance Optimization
1. **Index Implementation**
   - B-tree indexes
   - Hash indexes
   - Compound indexes

2. **Query Optimization**
   - Query plan optimization
   - Index usage optimization
   - Cache management

### 6.2 Advanced Features
1. **Distributed Transactions**
   - Two-phase commit
   - Distributed locking
   - Network partition handling

2. **Sharding Support**
   - Horizontal scaling
   - Data distribution
   - Load balancing

3. **Replication**
   - Master-slave replication
   - Read scaling
   - High availability

### 6.3 Monitoring and Management
1. **Performance Metrics**
   - Query performance
   - Lock contention
   - Transaction throughput

2. **Health Checks**
   - System status
   - Resource usage
   - Error detection

3. **Admin Interface**
   - System monitoring
   - Configuration management
   - User management

## 7. Usage Examples

### 7.1 Basic Operations
```python
# Create a database
db.create_database("mydb")

# Create a collection
db.create_collection("mydb", "users")

# Insert a document
db.execute_query("mydb", "insert into users {name: 'John', age: 30}")

# Query documents
db.execute_query("mydb", "find from users where age > 25")
```

### 7.2 Transaction Example
```python
# Start transaction
transaction_id = db.transaction_manager.begin_transaction()

try:
    # Perform operations
    db.execute_query("mydb", "insert into users {name: 'Alice'}")
    db.execute_query("mydb", "update users set age = 25 where name = 'Alice'")
    
    # Commit transaction
    db.transaction_manager.commit_transaction(transaction_id)
except Exception:
    # Rollback on failure
    db.transaction_manager.abort_transaction(transaction_id)
```

## 8. Best Practices

### 8.1 Transaction Management
1. Keep transactions short
2. Use appropriate isolation levels
3. Handle deadlocks gracefully
4. Implement proper error handling

### 8.2 Lock Management
1. Acquire locks in a consistent order
2. Release locks promptly
3. Use appropriate lock types
4. Monitor lock contention

### 8.3 Error Handling
1. Implement proper exception handling
2. Log errors appropriately
3. Provide meaningful error messages
4. Handle recovery gracefully

## 9. Troubleshooting

### 9.1 Common Issues
1. **Deadlocks**
   - Check transaction patterns
   - Review lock acquisition order
   - Monitor lock timeouts

2. **Performance Issues**
   - Check index usage
   - Monitor lock contention
   - Review transaction patterns

3. **Recovery Issues**
   - Check log files
   - Verify checkpoint integrity
   - Review recovery procedures

### 9.2 Debugging
1. Enable detailed logging
2. Monitor transaction states
3. Track lock acquisition
4. Review error logs

## 10. Conclusion
MangoDB provides a robust foundation for document-oriented database operations with full ACID compliance. Its implementation ensures data consistency, reliability, and proper handling of concurrent operations. The system is designed to be scalable and maintainable, with clear separation of concerns and comprehensive error handling. 