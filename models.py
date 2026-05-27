from config import get_logger
from pydantic import BaseModel,Field
logger = get_logger(__name__)

class AskRequest(BaseModel):
    question:str = Field(
        ...,
        max_length = 500,
        min_length=3,
        description="User query"
    )
    top_k :int =Field (default =3, ge=1,le=10,description ="Top results")
    category : str | None = None

class SourceDocument(BaseModel):
    source : str
    content_preview: str
    
class AskResponse(BaseModel):
    question:str
    answer:str
    sources: list[SourceDocument] =[]
    top_k:int
    
class HealthResponse(BaseModel):
    status:str
    service:str
    version:str
    document_indexed:int
    
class ErrorResponse(BaseModel):
    details:str
    error_type:str | None = None

class CacheStatsResponse(BaseModel):
    total_cached: int
    keys: list[str]