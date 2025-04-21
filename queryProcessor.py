import re

def match(doc, query):
    """
    Evaluates whether a document matches a MongoDB-style query.
    
    Supports:
    - Comparison: $eq, $ne, $gt, $lt, $gte, $lte
    - Set operators: $in, $nin
    - Field existence: $exists
    - Regex: $regex
    - Logical NOT: $not
    - Type check: $type
    - Array operations: $size, $all, $elemMatch
    - Modulo: $mod
    - Logical operators: $and, $or, $nor, $not
    """

    def evaluate_condition(field, condition):
        """
        Evaluates whether a single field in the document satisfies the condition.
        Supports embedded operators or direct value comparisons.
        """
        value = doc.get(field, None)  # Get value from doc, return None if not found

        # If the condition is a dictionary, it contains operators like $eq, $gt, etc.
        if isinstance(condition, dict):
            for op, expected in condition.items():

                # --- Comparison Operators ---
                if op == "$eq":  # Equal
                    if value != expected:
                        return False
                elif op == "$ne":  # Not equal
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

                # --- Set Operators ---
                elif op == "$in":  # Value is in the expected list
                    if value not in expected:
                        return False
                elif op == "$nin":  # Value is not in the expected list
                    if value in expected:
                        return False

                # --- Field Existence ---
                elif op == "$exists":  # Check if field exists or not
                    exists = field in doc
                    if expected and not exists:
                        return False
                    if not expected and exists:
                        return False

                # --- Regex Matching ---
                elif op == "$regex":  # Pattern match using regex
                    if not isinstance(value, str) or not re.search(expected, value):
                        return False

                # --- Logical NOT ---
                elif op == "$not":  # Negate a sub-condition
                    if evaluate_condition(field, expected):
                        return False

                # --- Type Check ---
                elif op == "$type":  # Match specific data type
                    type_map = {
                        "double": float,
                        "string": str,
                        "object": dict,
                        "array": list,
                        "bool": bool,
                        "int": int,
                        "null": type(None),
                    }
                    expected_type = type_map.get(expected, None)
                    if expected_type is None or not isinstance(value, expected_type):
                        return False

                # --- Array Size ---
                elif op == "$size":  # Match length of list
                    if not isinstance(value, list) or len(value) != expected:
                        return False

                # --- Array Contains All Elements ---
                elif op == "$all":  # Value must contain all specified elements
                    if not isinstance(value, list) or not all(item in value for item in expected):
                        return False

                # --- Element Match in Array ---
                elif op == "$elemMatch":  # At least one element must match the subquery
                    if not isinstance(value, list) or not any(
                        match(elem, expected) for elem in value if isinstance(elem, dict)
                    ):
                        return False

                # --- Modulo Check ---
                elif op == "$mod":  # value % divisor == remainder
                    if not isinstance(value, (int, float)) or value % expected[0] != expected[1]:
                        return False

                # --- Unknown operator ---
                else:
                    return False  # Unsupported operator

            return True  # All conditions for the field passed

        else:
            # If condition is not a dict, do a direct equality check
            return value == condition

    # --- Logical Operators at the top level of query ---

    if "$and" in query:  # All subqueries must match
        return all(match(doc, subquery) for subquery in query["$and"])

    if "$or" in query:  # At least one subquery must match
        return any(match(doc, subquery) for subquery in query["$or"])

    if "$nor" in query:  # None of the subqueries must match
        return not any(match(doc, subquery) for subquery in query["$nor"])

    if "$not" in query:  # Invert the entire condition
        return not match(doc, query["$not"])

    # --- Field-Level Query Processing ---
    for key, condition in query.items():
        if not evaluate_condition(key, condition):
            return False  # If any condition fails, return False

    return True  # All field conditions matched
