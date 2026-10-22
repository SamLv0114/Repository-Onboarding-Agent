from fastapi import APIRouter, HTTPException

from app.models.memory import ArchitectureMemory
from app.models.repository import AddRepositoryRequest, RepositorySummary
from app.services.ingestion import list_summaries, repository_summary, start_ingestion
from app.services.repositories import get_memory, get_repository

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=list[RepositorySummary])
def get_repositories() -> list[RepositorySummary]:
    return list_summaries()


@router.post("", response_model=RepositorySummary, status_code=202)
def add_repository(request: AddRepositoryRequest) -> RepositorySummary:
    """Clone a GitHub repository and onboard it in the background; poll for status."""
    try:
        return start_ingestion(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{repository_id}", response_model=RepositorySummary)
def get_repository_status(repository_id: str) -> RepositorySummary:
    return repository_summary(get_repository(repository_id))


@router.get("/{repository_id}/memory", response_model=ArchitectureMemory)
def get_repository_memory(repository_id: str) -> ArchitectureMemory:
    return get_memory(repository_id)
