import json
import os
from typing import Dict, List, Any, Optional
from bplus_tree import BPlusTree

class Index:
    def __init__(self, collection_name: str, field_name: str):
        self.collection_name = collection_name
        self.field_name = field_name
        self.tree = BPlusTree(order=4)  # B+ tree with order 4
        
    def add_entry(self, field_value: Any, document_id: str):
        """Add a document ID to the index for a given field value"""
        self.tree.insert(field_value, document_id)
            
    def remove_entry(self, field_value: Any, document_id: str):
        """Remove a document ID from the index for a given field value"""
        self.tree.remove(field_value, document_id)
                
    def find_documents(self, field_value: Any) -> List[str]:
        """Find all document IDs that match the given field value"""
        return self.tree.find(field_value)
        
    def to_dict(self) -> dict:
        """Convert index to dictionary for storage"""
        # Traverse B+ tree to get all data
        data = {}
        node = self.tree.root
        while node.leaf:
            for i, key in enumerate(node.keys):
                data[key] = node.values[i]
            node = node.next
            if not node:
                break
        
        return {
            "collection_name": self.collection_name,
            "field_name": self.field_name,
            "index_data": data
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'Index':
        """Create index from dictionary"""
        index = cls(
            data["collection_name"],
            data["field_name"]
        )
        # Rebuild B+ tree from stored data
        for key, doc_ids in data["index_data"].items():
            for doc_id in doc_ids:
                index.tree.insert(key, doc_id)
        return index

class IndexManager:
    def __init__(self, database_dir: str):
        self.database_dir = database_dir
        self.indexes_dir = os.path.join(database_dir, "indexes")
        os.makedirs(self.indexes_dir, exist_ok=True)
        self.indexes: Dict[str, Dict[str, Index]] = {}  # collection_name -> {field_name -> Index}
        
    def _get_index_path(self, collection_name: str, field_name: str) -> str:
        """Get the path to the index file"""
        return os.path.join(self.indexes_dir, f"{collection_name}_{field_name}_index.json")
        
    def create_index(self, collection_name: str, field_name: str) -> bool:
        """Create a new index for a collection field"""
        if collection_name not in self.indexes:
            self.indexes[collection_name] = {}
        if field_name in self.indexes[collection_name]:
            return False
            
        index = Index(collection_name, field_name)
        self.indexes[collection_name][field_name] = index
        self._save_index(index)
        return True
        
    def drop_index(self, collection_name: str, field_name: str) -> bool:
        """Drop an index for a collection field"""
        if collection_name in self.indexes and field_name in self.indexes[collection_name]:
            del self.indexes[collection_name][field_name]
            if not self.indexes[collection_name]:
                del self.indexes[collection_name]
            
            index_path = self._get_index_path(collection_name, field_name)
            if os.path.exists(index_path):
                os.remove(index_path)
            return True
        return False
        
    def get_index(self, collection_name: str, field_name: str) -> Optional[Index]:
        """Get an index for a collection field"""
        return self.indexes.get(collection_name, {}).get(field_name)
        
    def list_indexes(self, collection_name: str) -> List[str]:
        """List all indexed fields for a collection"""
        return list(self.indexes.get(collection_name, {}).keys())
        
    def _save_index(self, index: Index):
        """Save index to disk"""
        index_path = self._get_index_path(index.collection_name, index.field_name)
        with open(index_path, 'w') as f:
            json.dump(index.to_dict(), f, indent=2)
            
    def _load_index(self, collection_name: str, field_name: str) -> Optional[Index]:
        """Load index from disk"""
        index_path = self._get_index_path(collection_name, field_name)
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                data = json.load(f)
                return Index.from_dict(data)
        return None
        
    def update_index(self, collection_name: str, field_name: str, field_value: Any, document_id: str):
        """Update an index with a new document"""
        index = self.get_index(collection_name, field_name)
        if index:
            index.add_entry(field_value, document_id)
            self._save_index(index)
            
    def remove_from_index(self, collection_name: str, field_name: str, field_value: Any, document_id: str):
        """Remove a document from an index"""
        index = self.get_index(collection_name, field_name)
        if index:
            index.remove_entry(field_value, document_id)
            self._save_index(index)
            
    def find_documents(self, collection_name: str, field_name: str, field_value: Any) -> List[str]:
        """Find documents using an index"""
        index = self.get_index(collection_name, field_name)
        if index:
            return index.find_documents(field_value)
        return []
