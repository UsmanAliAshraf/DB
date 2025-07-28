class BPlusNode:
    def __init__(self, leaf=True, order=4):
        self.leaf = leaf
        self.keys = []
        self.values = []  # For leaf nodes: list of document IDs
        self.children = []  # For internal nodes: list of child nodes
        self.next = None  # For leaf nodes: pointer to next leaf
        self.order = order  # Maximum number of keys
        
    def is_full(self):
        return len(self.keys) >= self.order - 1

class BPlusTree:
    def __init__(self, order=4):
        self.root = BPlusNode(leaf=True, order=order)
        self.order = order
        
    def insert(self, key, doc_id):
        # If key exists, append doc_id to existing values
        if self.root.leaf:
            i = 0
            while i < len(self.root.keys) and self.root.keys[i] < key:
                i += 1
            if i < len(self.root.keys) and self.root.keys[i] == key:
                if doc_id not in self.root.values[i]:
                    self.root.values[i].append(doc_id)
                return
                
        # If root is full, create new root
        if self.root.is_full():
            new_root = BPlusNode(leaf=False, order=self.order)
            new_root.children = [self.root]
            self._split_child(new_root, 0)
            self.root = new_root
            
        self._insert_non_full(self.root, key, doc_id)
        
    def _insert_non_full(self, node, key, doc_id):
        i = len(node.keys) - 1
        
        if node.leaf:
            # Find position to insert
            while i >= 0 and node.keys[i] > key:
                node.keys.insert(i + 1, node.keys[i])
                node.values.insert(i + 1, node.values[i])
                i -= 1
                
            # Insert key and initialize empty list for doc_ids
            if i >= 0 and node.keys[i] == key:
                if doc_id not in node.values[i]:
                    node.values[i].append(doc_id)
            else:
                node.keys.insert(i + 1, key)
                node.values.insert(i + 1, [doc_id])
        else:
            # Find child to recurse
            while i >= 0 and node.keys[i] > key:
                i -= 1
            i += 1
            
            if node.children[i].is_full():
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
                    
            self._insert_non_full(node.children[i], key, doc_id)
            
    def _split_child(self, parent, i):
        order = self.order
        child = parent.children[i]
        new_node = BPlusNode(leaf=child.leaf, order=order)
        
        # Split the child
        mid = (order - 1) // 2
        parent.keys.insert(i, child.keys[mid])
        
        if child.leaf:
            # For leaf nodes, keep the key in both nodes
            new_node.keys = child.keys[mid:]
            new_node.values = child.values[mid:]
            child.keys = child.keys[:mid]
            child.values = child.values[:mid]
            # Update leaf node links
            new_node.next = child.next
            child.next = new_node
        else:
            # For internal nodes, move the middle key up
            new_node.keys = child.keys[mid + 1:]
            new_node.children = child.children[mid + 1:]
            child.keys = child.keys[:mid]
            child.children = child.children[:mid + 1]
            
        parent.children.insert(i + 1, new_node)
        
    def find(self, key):
        """Find all document IDs for a given key"""
        node = self.root
        while not node.leaf:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1
            node = node.children[i]
            
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
            
        if i < len(node.keys) and node.keys[i] == key:
            return node.values[i]
        return []
        
    def remove(self, key, doc_id):
        """Remove a document ID from the key's values"""
        node = self.root
        while not node.leaf:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1
            node = node.children[i]
            
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
            
        if i < len(node.keys) and node.keys[i] == key:
            if doc_id in node.values[i]:
                node.values[i].remove(doc_id)
                if not node.values[i]:  # If no more documents, remove the key
                    node.keys.pop(i)
                    node.values.pop(i)
