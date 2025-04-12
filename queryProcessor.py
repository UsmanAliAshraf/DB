# Check if a document matches the given query
# Example: doc = {"name": "Usman"} matches query = {"name": "Usman"}

def match(doc, query):
    """
    Check if a document matches the given query.
    Supports comparison operators ($eq, $ne, $gt, $lt, $gte, $lte)
    and logical operators ($and, $or).
    
    Args:
        doc (dict): The document to match against.
        query (dict): The query to evaluate.
        
    Returns:
        bool: True if the document matches, False otherwise.
    """

    def evaluate_condition(field, condition):
        """
        Evaluate a single field's condition on the document.
        
        Args:
            field (str): The field name in the document.
            condition (Any): The value or operator dict to compare against.
            
        Returns:
            bool: True if the condition is satisfied.
        """
        value = doc.get(field)

        # If condition is a dict, it's using operators like $gt, $eq, etc.
        if isinstance(condition, dict):
            for op, expected in condition.items():

                if op == "$eq":  # Equal to
                    if value != expected:
                        return False

                elif op == "$ne":  # Not equal to
                    if value == expected:
                        return False

                elif op == "$gt":  # Greater than
                    if value is None or value <= expected:
                        return False

                elif op == "$lt":  # Less than
                    if value is None or value >= expected:
                        return False

                elif op == "$gte":  # Greater than or equal
                    if value is None or value < expected:
                        return False

                elif op == "$lte":  # Less than or equal
                    if value is None or value > expected:
                        return False

                else:
                    return False  # Unknown/unsupported operator

            return True  # All operator conditions passed

        else:
            # If condition is not a dict, do a simple equality match
            return value == condition

    # --- Logical Operators Handling ---

    # $and: all subqueries must match
    if "$and" in query:
        return all(match(doc, subquery) for subquery in query["$and"])

    # $or: at least one subquery must match
    if "$or" in query:
        return any(match(doc, subquery) for subquery in query["$or"])

    # --- Standard Field-Based Matching ---

    # Check each field in the query
    for key, condition in query.items():
        if not evaluate_condition(key, condition):
            return False  # One failed match ends the check

    return True  # All conditions matched

