import redis
from fastapi import Depends,status,HTTPException,Request
from config import get_logger
from slowapi.util import get_remote_address

logger = get_logger(__name__)

def get_rag_chain():
    from main import rag_chain
    if rag_chain is None:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG not yet implemented"
        )
    return rag_chain

def get_redis()-> redis.Redis | None:
    from main import redis_client
    return redis_client

def get_redis_strict()->redis.Redis:
    from main import redis_client
    if redis_client is None:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail= "Redis unavailable"
        )
    return redis_client
        
class PaginationParams:
    def __init__(self,page:int =1, limit:int =10):
        if page <1:
            raise HTTPException(400,"Page must be >= 1")
        if limit >100:
            raise HTTPException(400,"Limit must not exceed 100")
        self.page = page
        self.limit =limit
    
    
def get_real_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)