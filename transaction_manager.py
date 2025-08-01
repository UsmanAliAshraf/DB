import time
import uuid
import json
import os
from enum import Enum
from threading import Lock, Timer
from datetime import datetime
from collections import defaultdict
import threading

class LockType(Enum):
    READ = "read"
    WRITE = "write"

class TransactionState(Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"
    BLOCKED = "blocked"

class IsolationLevel(Enum):
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"

class LockManager:
    def __init__(self, lock_timeout=30):  # 30 seconds default timeout
        self.locks = {}  # Nested dict: db -> collection -> doc_id -> lock_info
        self.lock_manager_lock = Lock()
        self.lock_timeout = lock_timeout
        self.wait_for_graph = defaultdict(set)  # For deadlock detection
        self.lock_waiters = defaultdict(list)  # Track waiting transactions

    def detect_deadlock(self, transaction_id):
        """Detect deadlocks using wait-for graph"""
        visited = set()
        path = set()

        def dfs(node):
            if node in path:
                return True  # Deadlock detected
            if node in visited:
                return False
            
            visited.add(node)
            path.add(node)
            
            for neighbor in self.wait_for_graph[node]:
                if dfs(neighbor):
                    return True
            
            path.remove(node)
            return False

        return dfs(transaction_id)

    def acquire_lock(self, db_name, collection, doc_id, lock_type, transaction_id, isolation_level):
        with self.lock_manager_lock:
            # Initialize nested structure if not exists
            if db_name not in self.locks:
                self.locks[db_name] = {}
            if collection not in self.locks[db_name]:
                self.locks[db_name][collection] = {}
            if doc_id not in self.locks[db_name][collection]:
                self.locks[db_name][collection][doc_id] = None

            current_lock = self.locks[db_name][collection][doc_id]
            
            # Check if lock can be acquired
            if current_lock is None:
                # No existing lock, can acquire
                self.locks[db_name][collection][doc_id] = {
                    "lock_type": lock_type.value,  # Store enum value
                    "transaction_id": transaction_id,
                    "timestamp": time.time(),
                    "isolation_level": isolation_level.value  # Store enum value
                }
                return True, "Lock acquired"
            
            # If same transaction, can upgrade lock
            if current_lock["transaction_id"] == transaction_id:
                if (lock_type == LockType.WRITE or 
                    (lock_type == LockType.READ and LockType(current_lock["lock_type"]) == LockType.READ)):
                    self.locks[db_name][collection][doc_id] = {
                        "lock_type": lock_type.value,  # Store enum value
                        "transaction_id": transaction_id,
                        "timestamp": time.time(),
                        "isolation_level": isolation_level.value  # Store enum value
                    }
                    return True, "Lock upgraded"
            
            # Check for deadlock
            self.wait_for_graph[transaction_id].add(current_lock["transaction_id"])
            if self.detect_deadlock(transaction_id):
                self.wait_for_graph[transaction_id].remove(current_lock["transaction_id"])
                return False, "Deadlock detected"
            
            # Add to waiters
            self.lock_waiters[(db_name, collection, doc_id)].append({
                "transaction_id": transaction_id,
                "lock_type": lock_type.value,  # Store enum value
                "timestamp": time.time()
            })
            
            return False, "Lock acquisition failed - waiting"

    def release_lock(self, db_name, collection, doc_id, transaction_id):
        with self.lock_manager_lock:
            if (db_name in self.locks and 
                collection in self.locks[db_name] and 
                doc_id in self.locks[db_name][collection]):
                
                current_lock = self.locks[db_name][collection][doc_id]
                if current_lock and current_lock["transaction_id"] == transaction_id:
                    self.locks[db_name][collection][doc_id] = None
                    
                    # Check waiters
                    key = (db_name, collection, doc_id)
                    if key in self.lock_waiters and self.lock_waiters[key]:
                        next_waiter = self.lock_waiters[key][0]
                        if time.time() - next_waiter["timestamp"] > self.lock_timeout:
                            # Remove timed out waiter
                            self.lock_waiters[key].pop(0)
                        else:
                            # Grant lock to next waiter
                            self.locks[db_name][collection][doc_id] = {
                                "lock_type": next_waiter["lock_type"],
                                "transaction_id": next_waiter["transaction_id"],
                                "timestamp": time.time(),
                                "isolation_level": IsolationLevel.READ_COMMITTED.value
                            }
                            self.lock_waiters[key].pop(0)
                    
                    return True
            return False

    def release_transaction_locks(self, transaction_id):
        with self.lock_manager_lock:
            for db_name in self.locks:
                for collection in self.locks[db_name]:
                    for doc_id in list(self.locks[db_name][collection].keys()):
                        if (self.locks[db_name][collection][doc_id] and 
                            self.locks[db_name][collection][doc_id]["transaction_id"] == transaction_id):
                            self.locks[db_name][collection][doc_id] = None
            
            # Clean up wait-for graph
            if transaction_id in self.wait_for_graph:
                del self.wait_for_graph[transaction_id]
            for node in self.wait_for_graph:
                if transaction_id in self.wait_for_graph[node]:
                    self.wait_for_graph[node].remove(transaction_id)

class TransactionManager:
    def __init__(self, base_dir, isolation_level=IsolationLevel.READ_COMMITTED):
        self.base_dir = base_dir
        self.lock_manager = LockManager()
        self.transactions = {}  # transaction_id -> transaction_info
        self.transaction_lock = Lock()
        self.log_dir = os.path.join(base_dir, "transaction_logs")
        self.checkpoint_dir = os.path.join(base_dir, "checkpoints")
        self.default_isolation_level = isolation_level
        self.last_checkpoint_time = time.time()
        self.checkpoint_interval = 60  # 60 seconds
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        # Start periodic checkpoint thread
        self.checkpoint_thread = threading.Thread(target=self._periodic_checkpoint, daemon=True)
        self.checkpoint_thread.start()

    def _periodic_checkpoint(self):
        """Create checkpoints periodically"""
        while True:
            time.sleep(1)  # Check every second
            current_time = time.time()
            if current_time - self.last_checkpoint_time >= self.checkpoint_interval:
                self._create_checkpoint()
                self.last_checkpoint_time = current_time
                # Clean up old transaction logs
                self._cleanup_old_logs()

    def _create_checkpoint(self, transaction_id=None):
        """Create a checkpoint of the current state"""
        checkpoint_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_time}.json")
        
        # Get all active transactions
        active_transactions = {
            tid: {
                **info,
                "locks": list(info["locks"])  # Convert set to list for JSON serialization
            }
            for tid, info in self.transactions.items()
            if info["state"] == TransactionState.ACTIVE.value
        }
        
        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "active_transactions": active_transactions,
            "last_checkpoint_time": self.last_checkpoint_time
        }
        
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)
        
        # Clean up old checkpoints
        self._cleanup_old_checkpoints()

    def _cleanup_old_checkpoints(self):
        """Keep only the last 5 checkpoints"""
        checkpoints = [f for f in os.listdir(self.checkpoint_dir) if f.startswith("checkpoint_")]
        if len(checkpoints) > 5:
            # Sort by timestamp and remove oldest
            checkpoints.sort()
            for old_checkpoint in checkpoints[:-5]:
                os.remove(os.path.join(self.checkpoint_dir, old_checkpoint))

    def _cleanup_old_logs(self):
        """Clean up transaction logs that have been checkpointed"""
        latest_checkpoint = self._get_latest_checkpoint()
        if not latest_checkpoint:
            return

        checkpoint_time = datetime.fromisoformat(latest_checkpoint["timestamp"])
        
        # For each database's transaction log
        for log_file in os.listdir(self.log_dir):
            if not log_file.endswith("_transactions.log"):
                continue
                
            log_path = os.path.join(self.log_dir, log_file)
            temp_path = log_path + ".temp"
            
            # Read and filter logs
            with open(log_path, "r") as f_in, open(temp_path, "w") as f_out:
                for line in f_in:
                    try:
                        log_entry = json.loads(line)
                        log_time = datetime.fromisoformat(log_entry["timestamp"])
                        # Keep only logs after the last checkpoint
                        if log_time > checkpoint_time:
                            f_out.write(line)
                    except json.JSONDecodeError:
                        continue
            
            # Replace old log with filtered log
            os.replace(temp_path, log_path)

    def begin_transaction(self, isolation_level=None):
        with self.transaction_lock:
            transaction_id = str(uuid.uuid4())
            try:
                last_checkpoint = self._get_latest_checkpoint()
            except:
                last_checkpoint = None
                
            self.transactions[transaction_id] = {
                "state": TransactionState.ACTIVE.value,
                "start_time": time.time(),
                "locks": set(),
                "isolation_level": (isolation_level or self.default_isolation_level).value,
                "last_checkpoint": last_checkpoint
            }
            return transaction_id

    def commit_transaction(self, transaction_id):
        with self.transaction_lock:
            if transaction_id not in self.transactions:
                return False, "Transaction not found"
            
            transaction = self.transactions[transaction_id]
            if transaction["state"] != TransactionState.ACTIVE.value:
                return False, f"Transaction is {transaction['state']}"
            
            # Release all locks
            self.lock_manager.release_transaction_locks(transaction_id)
            
            # Update transaction state
            transaction["state"] = TransactionState.COMMITTED.value
            transaction["end_time"] = time.time()
            
            return True, "Transaction committed successfully"

    def abort_transaction(self, transaction_id):
        with self.transaction_lock:
            if transaction_id not in self.transactions:
                return False, "Transaction not found"
            
            transaction = self.transactions[transaction_id]
            if transaction["state"] != TransactionState.ACTIVE.value:
                return False, f"Transaction is {transaction['state']}"
            
            # Release all locks
            self.lock_manager.release_transaction_locks(transaction_id)
            
            # Update transaction state
            transaction["state"] = TransactionState.ABORTED.value
            transaction["end_time"] = time.time()
            
            return True, "Transaction aborted successfully"

    def _get_latest_checkpoint(self):
        """Get the latest checkpoint information"""
        try:
            checkpoints = [f for f in os.listdir(self.checkpoint_dir) if f.startswith("checkpoint_")]
            if not checkpoints:
                return None
            
            latest_checkpoint = max(checkpoints)
            checkpoint_path = os.path.join(self.checkpoint_dir, latest_checkpoint)
            
            # Check if file exists and is not empty
            if not os.path.exists(checkpoint_path) or os.path.getsize(checkpoint_path) == 0:
                return None
                
            with open(checkpoint_path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    # If checkpoint is corrupted, try to delete it
                    try:
                        os.remove(checkpoint_path)
                    except:
                        pass
                    return None
        except Exception as e:
            print(f"Error reading checkpoint: {str(e)}")
            return None

    def recover_from_checkpoint(self):
        """Recover the system state from the latest checkpoint"""
        latest_checkpoint = self._get_latest_checkpoint()
        if not latest_checkpoint:
            return False, "No checkpoint found"
        
        # Implement recovery logic here
        # This would involve:
        # 1. Reading the checkpoint
        # 2. Replaying logs since the checkpoint
        # 3. Restoring the system state
        
        return True, "Recovery completed"

    def log_operation(self, transaction_id, operation, db_name, collection, doc_id, before_state, after_state):
        log_entry = {
            "transaction_id": transaction_id,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "db_name": db_name,
            "collection": collection,
            "document_id": doc_id,
            "before_state": before_state,
            "after_state": after_state,
            "isolation_level": self.transactions[transaction_id]["isolation_level"]
        }
        
        # Create log file for the database if it doesn't exist
        log_file = os.path.join(self.log_dir, f"{db_name}_transactions.log")
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_transaction_state(self, transaction_id):
        with self.transaction_lock:
            if transaction_id not in self.transactions:
                return None
            return TransactionState(self.transactions[transaction_id]["state"])

    def acquire_document_lock(self, db_name, collection, doc_id, lock_type, transaction_id):
        if self.get_transaction_state(transaction_id) != TransactionState.ACTIVE:
            return False, "Transaction is not active"
        
        isolation_level = IsolationLevel(self.transactions[transaction_id]["isolation_level"])
        success, message = self.lock_manager.acquire_lock(
            db_name, collection, doc_id, lock_type, transaction_id, isolation_level
        )
        
        if success:
            self.transactions[transaction_id]["locks"].add((db_name, collection, doc_id))
            if message == "Lock acquisition failed - waiting":
                self.transactions[transaction_id]["state"] = TransactionState.BLOCKED.value
            return True, message
        return False, message 