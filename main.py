from config import get_logger,APP_VERSION,APP_TITLE,TOP_K,CHROMA_DIR
from fastapi import FastAPI, status, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from rag import ensure_index_exists,load_chat_model,load_embedding_model,rag_chain_method
from contextlib import asynccontextmanager
from models import AskRequest,SourceDocument,AskResponse,HealthResponse

logger = get_logger(__name__)
rag_chain =None
retriever =None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_chain, retriever, llm, embedding
    llm = load_chat_model()
    embedding = load_embedding_model()
    
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

def get_rag_chain():
    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail = "RAG Exception occured"
        )
    return rag_chain
    
@app.get("/health", response_model=HealthResponse)
async def health_check()->HealthResponse:
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
async def ask(request: AskRequest,chain = Depends(get_rag_chain)):
    results = await rag_chain.ainvoke(request.question)
    answer = results.get("answer","")
    source_doc = results.get("sources",[])
    sources = [
        SourceDocument(
            source=src.metadata.get("source","unknown"),
            content_preview=src.page_content[:100]
        )
        for src in source_doc
        ]
    return {
        "question" : request.question,
        "answer": answer,
        "sources": sources,
        "top_k":TOP_K
    }