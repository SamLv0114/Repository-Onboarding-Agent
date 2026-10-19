from fastapi import APIRouter
from app.models.memory import ArchitectureMemory
from app.services.repositories import get_memory

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("")
def get_repositories() -> list[dict[str, str]]:
    return [{"repository_id": "demo-repo", "name": "Demo Repository", "snapshot_id": "demo-snapshot-v1"}]


@router.get("/{repository_id}/memory", response_model=ArchitectureMemory)
def get_repository_memory(repository_id: str) -> ArchitectureMemory:
    return get_memory(repository_id)
