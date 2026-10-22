import os

from fastapi import APIRouter

from app.agents.qa_graph import answer_question
from app.models.qa import QARequest, QAResponse
from app.services.qa import run_qa

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=QAResponse)
def ask_question(request: QARequest) -> QAResponse:
    # QA_ENGINE=demo keeps the offline keyword demo, which needs no OpenAI key.
    if os.getenv("QA_ENGINE", "agent") == "demo":
        return run_qa(request)
    return answer_question(request)
