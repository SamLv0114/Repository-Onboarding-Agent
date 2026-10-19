from fastapi import APIRouter

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/summary")
def benchmark_summary() -> dict:
    return {
        "available": False,
        "message": "Evaluation integration pending; no benchmark measurements are available.",
        "metrics": [],
    }
