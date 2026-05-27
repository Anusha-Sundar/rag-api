from config import get_logger,APP_VERSION,APP_TITLE,TOP_K,CHROMA_DIR,TTL
from fastapi import FastAPI, status, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from rag import ensure_index_exists,load_chat_model,load_embedding_model,rag_chain_method
from contextlib import asynccontextmanager
from models import AskRequest,SourceDocument,AskResponse,HealthResponse,CacheStatsResponse
from cache import get_redis_client,get_cached,set_cached,get_cache_stats
import redis
import time
from slowapi import Limiter,_rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dependencies import get_rag_chain,get_redis,get_redis_strict,PaginationParams,get_real_ip
from typing import Annotated
logger = get_logger(__name__)
rag_chain =None
retriever =None
redis_client = None

RagChain = Annotated[any,Depends(get_rag_chain)]
RedisClientStrict= Annotated[redis.Redis, Depends(get_redis_strict)]
RedisClient= Annotated[redis.Redis | None, Depends(get_redis)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_chain, retriever, llm, embedding,redis_client
    llm = load_chat_model()
    embedding = load_embedding_model()
    redis_client = get_redis_client()
    try:
        redis_client.ping()
        logger.info("Connection success")
    except Exception as e:
        logger.error(f"Redis connection failed due to : {type(e).__name__} : {e}")
        redis_client=None
    # Build index from default PDF at startup
    vectorstore = ensure_index_exists(
        pdf_path="data/AI_Technical_Corpus_v1.pdf",
        persist_dir=CHROMA_DIR,
        embedding=embedding
    )
    rag_chain, retriever = rag_chain_method(llm, vectorstore)
    logger.info("Startup complete")
    yield
    
app = FastAPI(title=APP_TITLE,version=APP_VERSION,lifespan=lifespan) 
limiter = Limiter(key_func=get_real_ip) 
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc:Exception):
    err=f"{request.url} URL has issues : {type(exc).__name__} : {exc}"
    logger.error(err)
    return JSONResponse(
        status_code = 500,
        content = {
            "details": "Uncexpected error occured",
            "error_type": type(exc).__name__
        }
    )
    
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request,exc:RequestValidationError):
    errors = exc.errors()
    logger.warning(f"{request.url} URL has issues : {errors}")
    return JSONResponse(
        status_code =422,
        content = {
            "details": "Request validation failed",
            "error_type":[
            {
                "field": ".".join([str(loc) for loc in err["loc"]]),
                "type":err["type"],
                "message": err["msg"]
            }
            for err in errors
        ]
        }
    )

@app.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
async def health_check(request: Request)->HealthResponse:
    rag_status = "OK" if rag_chain is not None else "degraded"
    doc_count =0
    if retriever is not None:
        try:
            doc_count = retriever.vectorstore._collection.count()
        except Exception as e:
            logger.error(f"Exception occured: {type(e).__name__} :{e}")
            rag_status = "degraded"
    return HealthResponse(
        status =rag_status,
        service = "RAG API",
        version ="1.0.0",
        document_indexed = doc_count
    )

@app.post("/ask", response_model = AskResponse)
@limiter.limit("10/minute")
async def ask(request: Request,req: AskRequest,cache:RedisClient,chain = Depends(get_rag_chain)):
    if cache is not None:
        cached = get_cached(redis_client,req.question)
        if cached is not None:
            return AskResponse(**cached)
    if not req.question.strip():
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail = "Question cannot be empty"
        )
    
    try:
        start = time.time()
        results = await rag_chain.ainvoke(req.question)
        timeval = round(((time.time() -start) *1000),2)
        logger.info(f"Rag chain completed in {timeval}ms")
    except Exception as e:
        logger.error(f"Chain failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail ="RAG System not avialable temporary glitch"
        )
    answer = results.get("answer","")
    source_doc = results.get("sources",[])
    sources = [
        SourceDocument(
            source=src.metadata.get("source","unknown"),
            content_preview=src.page_content[:100]
        )
        for src in source_doc
        ]
    response = AskResponse(
        question= req.question,
        answer= answer,
        sources = sources,
        top_k=TOP_K
    )
    if cache is not None:
        set_cached(cache,req.question,response.model_dump(),TTL)
        
    return response

@app.get("/cache/stats")
@limiter.limit("5/minute")
def cache_status(request: Request,cache:RedisClientStrict)->CacheStatsResponse:
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available"
        )
    stats =get_cache_stats(cache)
    return CacheStatsResponse(**stats)

@app.delete("/cache/clear")
@limiter.limit("5/minute")
def cache_status(request: Request,cache:RedisClientStrict)-> dict:
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available"
        )
    keys = cache.keys("rag:*")
    if keys:
        cache.delete(*keys)
    logger.info(f"Cleared total of {len(keys)} entries")
    return {"cleared": len(keys)}


@app.get("/documents")
@limiter.limit("30/minute")
async def list_documents(request: Request,pagination=Depends(PaginationParams)) -> dict:
    return {
        "page": pagination.page,
        "limit": pagination.limit,
        "message": "Document listing endpoint — pagination working"
    }