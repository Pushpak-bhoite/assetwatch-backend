from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items tag"])

@router.get("/")
def getAllItems():
    return {"all items": 'hello all items'} 

