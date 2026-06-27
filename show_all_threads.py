import sqlite3
from loan_sanction_application import graph

def show_all_threads():
    # 1. Connect to the NEW Loan SQLite database to get all unique thread IDs
    conn = sqlite3.connect("loans_database.sqlite")
    cursor = conn.cursor()
    
    # Checkpoints table stores the state for all threads
    try:
        # Order by MAX(checkpoint_id) DESC so the most recently updated thread appears first
        cursor.execute("SELECT thread_id FROM checkpoints GROUP BY thread_id ORDER BY MAX(checkpoint_id) DESC;")
        thread_ids = [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table might not exist if the script was never run
        thread_ids = []
    
    print(f"\n🔍 Found {len(thread_ids)} unique LOAN threads in the database (Sorted Newest to Oldest).")
    print("=" * 70)
    
    # 2. For each thread ID, ask the graph to get its current/final state
    for tid in thread_ids:
        config = {"configurable": {"thread_id": tid}}
        
        # Pull the state using LangGraph
        try:
            state = graph.get_state(config).values
            
            status = state.get("status", "Unknown")
            req_amount = state.get("requested_amount", 0)
            sanc_amount = state.get("sanctioned_amount", 0)
            int_rate = state.get("interest_rate", 0.0)
            profit = state.get("expected_profit", 0.0)
            approved = state.get("manager_approval", False)
            notes = state.get("notes", "No notes")
            
            # Display the result with Indian currency formatting
            print(f"Thread ID          : {tid}")
            print(f"Requested Amount   : ₹{req_amount:,}")
            print(f"Sanctioned Amount  : ₹{sanc_amount:,}")
            print(f"Interest Rate      : {int_rate}%")
            print(f"Expected Profit    : ₹{profit:,.2f}")
            print(f"Status             : {status.upper()}")
            print(f"Manager Approved?  : {approved}")
            print(f"Manager Notes      : {notes}")
            print("-" * 70)
        except Exception as e:
            print(f"Thread ID: {tid} | Error reading state: {e}")

if __name__ == "__main__":
    show_all_threads()
