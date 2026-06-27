import sqlite3
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

# ==========================================
# CONFIGURATION
# ==========================================
MIN_SANCTION_AMOUNT = 100000   # 1 Lakh
MAX_SANCTION_AMOUNT = 1000000  # 10 Lakhs
MIN_INTEREST_RATE = 5.0
MAX_INTEREST_RATE = 15.0
DEFAULT_INTEREST_RATE = 10.0

# ==========================================
# 1. DEFINE THE STATE (Memory structure)
# ==========================================
class LoanState(TypedDict):
    requested_amount: int
    sanctioned_amount: int
    interest_rate: float
    expected_profit: float
    status: str
    notes: str
    manager_approval: bool
    is_modified: bool

# ==========================================
# 2. DEFINE THE NODES (Actions)
# ==========================================
def request_loan(state: LoanState):
    print(f"🤖 [System]: Loan requested for ₹{state.get('requested_amount'):,}.")
    return {"status": "pending_approval", "sanctioned_amount": 0, "expected_profit": 0.0}

def process_loan(state: LoanState):
    notes = state.get('notes', 'No notes provided.')
    is_modified = state.get('is_modified', False)
    if state.get("manager_approval"):
        print(f"✅ [System]: SUCCESS - Processing loan of ₹{state.get('sanctioned_amount'):,} at {state.get('interest_rate')}% interest.")
        print(f"💰 [System]: Expected Bank Profit: ₹{state.get('expected_profit'):,.2f}")
        print(f"📝 [Manager Notes]: {notes}")
        if is_modified:
            return {"status": "modified_and_approved"}
        else:
            return {"status": "approved"}
    else:
        print(f"❌ [System]: REJECTED - Loan request for ₹{state.get('requested_amount'):,} was denied.")
        print(f"📝 [Manager Notes]: {notes}")
        return {"status": "rejected"}

# ==========================================
# 3. BUILD THE GRAPH
# ==========================================
builder = StateGraph(LoanState)

builder.add_node("request_loan", request_loan)
builder.add_node("process_loan", process_loan)

builder.add_edge(START, "request_loan")
builder.add_edge("request_loan", "process_loan")
builder.add_edge("process_loan", END)

# ==========================================
# 4. COMPILE WITH DATABASE & INTERRUPTION
# ==========================================
conn = sqlite3.connect("loans_database.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["process_loan"]
)

# Helper function to calculate profit (Simple Interest for 1 year)
def calculate_profit(amount, rate):
    return (amount * rate) / 100

# ==========================================
# SIMULATING THE REAL-WORLD TIMELINE
# ==========================================
if __name__ == "__main__":
    
    unique_thread_id = f"loan_txn_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": unique_thread_id}}

    print(f"\n--- DAY 1: CUSTOMER REQUESTS LOAN ({unique_thread_id}) ---")
    
    initial_input = {
        "requested_amount": 500000, 
        "sanctioned_amount": 0,
        "interest_rate": DEFAULT_INTEREST_RATE,
        "expected_profit": 0.0,
        "manager_approval": False, 
        "status": "initiated",
        "notes": "",
        "is_modified": False
    }
    
    for event in graph.stream(initial_input, config):
        pass 
        
    print("⏸️  [System]: Graph paused. Context safely stored in SQLite database.")
    print("💤 [System]: Server can now sleep or handle other requests...\n")
    
    print("--- DAY 2: BANK MANAGER LOGS IN ---")
    current_state = graph.get_state(config).values
    req_amt = current_state.get('requested_amount')
    current_interest = current_state.get('interest_rate')
    
    print(f"🔍 [Manager]: Inspecting request... Customer wants ₹{req_amt:,}.")
    
    # Manager simulation loop
    sanc_amt = req_amt
    int_rate = current_interest
    is_approved = False
    manager_notes = ""
    is_modified = False
    
    while True:
        profit = calculate_profit(sanc_amt, int_rate)
        print(f"\n📊 [Dashboard]: If you sanction ₹{sanc_amt:,} at {int_rate}%, the bank's expected profit is ₹{profit:,.2f}.")
        
        decision = input("👤 [Manager]: Type 'approve' to finalize, 'modify' to change amount/interest, or 'reject' to deny: ").strip().lower()
        
        if decision == 'approve':
            is_approved = True
            is_modified = False
            manager_notes = input("👤 [Manager]: Enter approval notes: ")
            break
        elif decision == 'modify':
            # 1. Modify Sanctioned Amount
            while True:
                try:
                    amt_input = input(f"   Enter new sanction amount (Min ₹{MIN_SANCTION_AMOUNT:,}, Max ₹{MAX_SANCTION_AMOUNT:,}): ").replace(',', '')
                    new_amt = int(amt_input)
                    if MIN_SANCTION_AMOUNT <= new_amt <= MAX_SANCTION_AMOUNT:
                        sanc_amt = new_amt
                        break
                    else:
                        print(f"   ⚠️ Amount must be between ₹{MIN_SANCTION_AMOUNT:,} and ₹{MAX_SANCTION_AMOUNT:,}.")
                except ValueError:
                    print("   ⚠️ Please enter a valid number.")
                    
            # 2. Modify Interest Rate
            while True:
                try:
                    rate_input = input(f"   Enter new interest rate (Min {MIN_INTEREST_RATE}%, Max {MAX_INTEREST_RATE}%): ")
                    new_rate = float(rate_input)
                    if MIN_INTEREST_RATE <= new_rate <= MAX_INTEREST_RATE:
                        int_rate = new_rate
                        break
                    else:
                        print(f"   ⚠️ Interest rate must be between {MIN_INTEREST_RATE}% and {MAX_INTEREST_RATE}%.")
                except ValueError:
                    print("   ⚠️ Please enter a valid number.")
            
            manager_notes = input("👤 [Manager]: Enter modification notes: ")
            is_approved = True
            is_modified = True
            break
        else:
            is_approved = False
            is_modified = False
            manager_notes = input("👤 [Manager]: Enter rejection notes: ")
            break

    if is_approved:
        print(f"\n✅ [System]: Manager approved loan of ₹{sanc_amt:,} at {int_rate}%.")
    else:
        print("\n❌ [System]: Manager rejected the request.")
        
    # Update state in DB
    final_profit = calculate_profit(sanc_amt, int_rate) if is_approved else 0.0
    
    graph.update_state(config, {
        "manager_approval": is_approved,
        "sanctioned_amount": sanc_amt if is_approved else 0,
        "interest_rate": int_rate if is_approved else 0.0,
        "expected_profit": final_profit,
        "notes": manager_notes,
        "is_modified": is_modified
    })
    
    print("\n▶️  [System]: Resuming execution...")
    for event in graph.stream(None, config):
        pass
        
    print(f"\n--- TRANSACTION COMPLETE ({unique_thread_id}) ---")
    final_state = graph.get_state(config).values
    print(f"Final Database State for {unique_thread_id}: {final_state}")
