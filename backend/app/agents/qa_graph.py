"""LangGraph integration placeholder — NOT wired into the demo API yet.

Planned graph:
  retrieve_memory -> assess_evidence -> [answer | live_search] -> answer -> END

When implementing, prefer a typed state with separate fields for:
- original question, repository ID, snapshot ID
- candidate claims, evidence, routing decision
- actual tool calls / token usage / errors
- final response + validated citations

Use `langgraph` (pip install -e '.[agent]') and write unit tests for both branches
before replacing `run_qa` in the API router. Importing LangGraph prematurely here
would make simple scaffold startup depend on the optional provider stack.
"""
