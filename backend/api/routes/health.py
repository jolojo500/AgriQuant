from fastapi import APIRouter

router = APIRouter()

@router.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    """Render will stay up, using uptimerobot and this to verify the API is running."""
    return {"status": "ok"}