import uuid
from typing import Dict, Any, Optional, List
import json
import os

class DocumentValidator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.unique_indexes = {}  # collection -> {field_name: index_file_path}

    def ensure_id_field(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure document has a unique _id field."""
        if '_id' not in document:
            document['_id'] = str(uuid.uuid4())
        return document

    def create_unique_index(self, collection: str, field: str) -> bool:
        """Create a unique index on a field."""
        index_dir = os.path.join(self.db_path, collection, 'indexes')
        os.makedirs(index_dir, exist_ok=True)
        
        index_file = os.path.join(index_dir, f"{field}.idx")
        
        # Initialize index if it doesn't exist
        if not os.path.exists(index_file):
            with open(index_file, 'w') as f:
                json.dump({}, f)
        
        if collection not in self.unique_indexes:
            self.unique_indexes[collection] = {}
        self.unique_indexes[collection][field] = index_file
        return True

    def validate_document(self, collection: str, document: Dict[str, Any], 
                         is_update: bool = False, old_doc: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        """Validate document against schema rules and unique constraints."""
        # Ensure _id field exists
        document = self.ensure_id_field(document)
        
        # Check unique constraints
        if collection in self.unique_indexes:
            for field, index_file in self.unique_indexes[collection].items():
                if field in document:
                    # Skip uniqueness check for the same document during update
                    if is_update and old_doc and old_doc.get(field) == document[field]:
                        continue
                        
                    if not self._check_unique_constraint(collection, field, document[field], document['_id']):
                        return False, f"Duplicate value for unique field '{field}'"
        
        return True, ""

    def _check_unique_constraint(self, collection: str, field: str, value: Any, doc_id: str) -> bool:
        """Check if a value is unique in the index."""
        index_file = self.unique_indexes[collection][field]
        
        try:
            with open(index_file, 'r') as f:
                index = json.load(f)
            
            # Convert value to string for JSON compatibility
            value_str = str(value)
            
            # Check if value exists and belongs to a different document
            if value_str in index and index[value_str] != doc_id:
                return False
            
            # Update index
            index[value_str] = doc_id
            with open(index_file, 'w') as f:
                json.dump(index, f)
            
            return True
        except Exception as e:
            print(f"Error checking unique constraint: {str(e)}")
            return False

    def remove_from_index(self, collection: str, field: str, value: Any) -> None:
        """Remove a value from the unique index."""
        if collection in self.unique_indexes and field in self.unique_indexes[collection]:
            index_file = self.unique_indexes[collection][field]
            try:
                with open(index_file, 'r') as f:
                    index = json.load(f)
                
                value_str = str(value)
                if value_str in index:
                    del index[value_str]
                    
                with open(index_file, 'w') as f:
                    json.dump(index, f)
            except Exception as e:
                print(f"Error removing from index: {str(e)}")

    def get_indexed_fields(self, collection: str) -> List[str]:
        """Get list of indexed fields for a collection."""
        return list(self.unique_indexes.get(collection, {}).keys()) 