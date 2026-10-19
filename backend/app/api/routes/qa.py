from fastapi import APIRouter
from app.models.qa import QARequest, QAResponse
from app.services.qa import run_qa

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=QAResponse)
def ask_question(request: QARequest) -> QAResponse:
    return run_qa(request)
