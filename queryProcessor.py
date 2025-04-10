# Check if a document matches the given query
# Example: doc = {"name": "Usman"} matches query = {"name": "Usman"}

def match(doc, query):
    # Go through each query key and see if it matches the doc's values
    return all(doc.get(k) == v for k, v in query.items())
