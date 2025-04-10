from query_parser import process_query

def main():
    print("📦 Simple DocumentDB CLI")
    print("Type your queries like MongoDB:")
    print("→ INSERT {\"id\": 1, \"name\": \"Usman\"}")
    print("→ FIND {\"name\": \"Usman\"}")
    print("→ UPDATE {\"id\": 1} {\"$set\": {\"name\": \"Ali\"}}")
    print("→ DELETE {\"id\": 1}")
    print("Type 'exit' to quit.\n")

    collection = "users"  # Default collection name

    while True:
        user_input = input(">>> ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Exiting. Bye!")
            break

        result = process_query(user_input, collection)
        print(result)

if __name__ == "__main__":
    main()
