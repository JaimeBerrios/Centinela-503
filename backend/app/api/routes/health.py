from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_check():
    return {
        "status": "ok", 
        "message": "Centinela 503 API operando correctamente."
    }