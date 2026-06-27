# LangGraph Human-in-the-Loop: Loan Sanction System

A simple, crystal-clear demonstration of a Human-in-the-Loop (HITL) workflow using **LangGraph** and **SQLite**. This system runs an automated workflow, pauses to wait for manual human input (Bank Manager approval/modification), and then seamlessly resumes.

---

## 🔄 The Workflow

1. **Initiation (`DAY 1`)**
   A customer requests a loan (e.g., ₹5,00,000). The system runs the first node (`request_loan`).
2. **Pause & Checkpoint**
   The graph is configured to explicitly pause *before* running the final node (`process_loan`). LangGraph automatically takes a snapshot of the current variables (state) and saves it to the SQLite database. The system goes to sleep.
3. **Manager Intervention (`DAY 2`)**
   The Bank Manager logs in. The system fetches the paused state from the database. The manager is presented with a dashboard showing expected bank profits.
4. **Decision & Update**
   The manager can:
   - **Approve:** Accept the exact amount requested.
   - **Modify:** Change the sanctioned amount (between 1L - 10L) and interest rate (5% - 15%).
   - **Reject:** Deny the loan.
   The manager also adds custom notes. This new decision is forcefully updated in the LangGraph state.
5. **Resumption**
   The system tells the graph to resume from exactly where it left off. The final node (`process_loan`) executes, checking the manager's updated state, and finishes the transaction.

---

## 🧠 Why Memory & Persistence?

In a real-world scenario, an employee might request a loan on a Friday, and the Bank Manager might not log in to approve it until Monday. 

If this application relied entirely on standard server memory (RAM), the workflow would be completely lost the moment the server went to sleep, crashed, or restarted. 

**How the code achieves persistence:**
By passing `checkpointer=memory` (which is powered by `SqliteSaver`) into the graph compiler, we give the workflow **fault-tolerant persistence**. Every time the graph reaches a pause point, it writes its exact variables to the physical hard drive. The Python script can completely exit, and days can pass. When the manager finally acts, we give LangGraph the unique `thread_id`, and it pulls the state from the hard drive back into RAM, resuming exactly as if no time had passed.

---

## 💾 Database Details (`loans_database.sqlite`)

LangGraph uses this SQLite database strictly as **short-term working memory**. 

- **The `checkpoints` Table:** This is the core table. LangGraph automatically saves the state here after every single node execution. The data is stored in a highly compressed binary format (`MsgPack`), so it cannot be read using standard `SELECT *` SQL queries.
- **Dynamic Thread IDs:** Every single loan request is assigned a unique UUID (e.g., `loan_txn_929ef35a`). This ID is used to isolate transactions. Because every user gets a unique ID, thousands of loans can pause and resume simultaneously without colliding.
- **Extracting Data:** To read the data, you don't use raw SQL. Instead, you query the unique thread ID using LangGraph's API (`graph.get_state(config)`). This pulls the binary blob out of SQLite and converts it back into a readable Python dictionary.

---

## 🚀 How to Run

**1. Run the Main Simulation**
Execute the main script to simulate a user requesting a loan and a manager making a decision.
```bash
python3 loan_sanction_application.py
```
*(Follow the interactive terminal prompts to approve, modify, or reject.)*

**2. View the Manager Dashboard**
Execute the dashboard script to view a history of all loans processed in the database, ordered from newest to oldest.
```bash
python3 show_all_threads.py
```
*(This script scans the `checkpoints` table for all unique thread IDs and extracts their final readable states).*
