from fastapi import APIRouter

router = APIRouter(
    prefix="/api/ai",
    tags=["AI"],
)

@router.get("/health")
async def ai_health():
    return {
        "status": "ok",
        "module": "ai",
    }
