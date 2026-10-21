from pathlib import Path

from dotenv import load_dotenv

from app.agents.qa_graph import build_qa_graph

load_dotenv(Path(__file__).resolve().parents[1] / ".env")



graph = build_qa_graph()

result = graph.invoke(
    {
        "question": ("How does authentication refresh token rotation work?"),
        "repository_id": "demo-repo",
        "strategy": "memory_first",
    },
    config={
        "run_name": "AMS691-QA-MemoryFirst",
        "tags": ["development", "memory-first"],
    },
)

print("Route:", result["route"])
print("Decision:", result.get("decision"))
