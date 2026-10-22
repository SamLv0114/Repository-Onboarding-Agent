from pathlib import Path

from dotenv import load_dotenv

from app.agents.qa_graph import answer_question
from app.models.qa import QARequest

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


response = answer_question(
    QARequest(
        repository_id="demo-repo",
        question="How does authentication refresh token rotation work?",
        strategy="memory_first",
    )
)

print("Route:", response.strategy_used)
print("Status:", response.answer_status)
print("Answer:", response.answer)
print("Usage:", response.usage)
