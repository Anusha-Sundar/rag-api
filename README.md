# RAG API

A production-grade Retrieval Augmented Generation API built with LangChain, ChromaDB, and FastAPI. Deployed on Azure Container Apps with automated CI/CD via GitHub Actions.

## Live Demo

| | |
|---|---|
| **Base URL** | https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io |
| **Swagger UI** | https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io/docs |
| **Health Check** | https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io/health |

## Architecture

```
┌─────────────┐     POST /ask      ┌─────────────────┐
│   Client    │ ─────────────────► │   FastAPI App   │
│ (curl/UI)   │                    │  (Container App) │
└─────────────┘                    └────────┬────────┘
                                            │
                              ┌─────────────▼─────────────┐
                              │        RAG Pipeline        │
                              │                            │
                              │  1. Embed question         │
                              │     (all-MiniLM-L6-v2)    │
                              │                            │
                              │  2. Vector search          │
                              │     (ChromaDB)             │
                              │                            │
                              │  3. Build prompt           │
                              │     (LangChain LCEL)       │
                              │                            │
                              │  4. Generate answer        │
                              │     (Groq LLaMA 3.1)      │
                              └─────────────┬─────────────┘
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │  Answer + Source Docs    │
                              └─────────────────────────┘

CI/CD Pipeline:
┌──────────┐    git push    ┌─────────────────┐    build + push    ┌─────────┐
│ Your Mac │ ─────────────► │ GitHub Actions  │ ─────────────────► │   ACR   │
└──────────┘                │  (Ubuntu VM)    │                    └────┬────┘
                            └─────────────────┘                         │
                                                                         │ pull
                                                                    ┌────▼────────────┐
                                                                    │ Azure Container │
                                                                    │      Apps       │
                                                                    └─────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI — async REST, auto Swagger UI |
| RAG Orchestration | LangChain LCEL — retriever + LLM chain |
| Vector Store | ChromaDB — persistent local embeddings |
| Embedding Model | sentence-transformers/all-MiniLM-L6-v2 |
| LLM | Groq — llama-3.1-8b-instant |
| Containerisation | Docker — python:3.11-slim, non-root user |
| Image Registry | Azure Container Registry (Basic tier) |
| Deployment | Azure Container Apps — serverless, 1 replica |
| CI/CD | GitHub Actions — auto deploy on push to main |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service status and document count |
| POST | `/ask` | Ask a question, get grounded answer with sources |
| GET | `/docs` | Interactive Swagger UI |

### Request Schema — POST /ask

```json
{
  "question": "What is RAG?",
  "top_k": 3,
  "category": null
}
```

| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| question | string | Yes | — | min 3 chars, max 500 chars |
| top_k | int | No | 3 | 1 to 10 |
| category | string | No | null | metadata filter |

### Response Schema

```json
{
  "question": "What is RAG?",
  "answer": "RAG stands for Retrieval-Augmented Generation...",
  "sources": [
    {
      "source": "data/AI_Technical_Corpus_v1.pdf",
      "content_preview": "RAG systems work in two phases: indexing and retrieval..."
    }
  ],
  "top_k": 3
}
```

## Example Usage

**Health check:**
```bash
curl https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io/health
```

**Ask a question:**
```bash
curl -X POST https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "top_k": 3}'
```

**Hallucination test — question outside the corpus:**
```bash
curl -X POST https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the population of Chennai?"}'
```

Expected: `"I do not have information about the query."` — hallucination prevention working.

## Local Development

```bash
# Build
docker build -t rag-api:latest .

# Run
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key_here \
  rag-api:latest

# Test
curl http://localhost:8000/health
```

## How It Works

**Startup:** When the container starts, it loads the embedding model and LLM, then builds a ChromaDB vector index from the pre-loaded PDF corpus. All 12 chunks are indexed and ready before the first request arrives.

**Query flow:** A question comes in via POST /ask. The embedding model converts it to a vector. ChromaDB finds the 3 most semantically similar chunks. LangChain builds a prompt with those chunks as context. Groq generates a grounded answer. The response includes the answer and the source documents used.

**Hallucination prevention:** The system prompt instructs the LLM to answer only from the provided context. Questions outside the corpus return "I do not have information about the query" instead of hallucinated answers.

## CI/CD Pipeline

Every push to `main` triggers an automated deployment:

```
git push origin main
       ↓
GitHub Actions runner starts (Ubuntu)
       ↓
Checks out code
       ↓
Logs into Azure via Service Principal
       ↓
Builds AMD64 Docker image (cross-platform from Mac ARM64)
       ↓
Pushes image to Azure Container Registry
       ↓
Updates Azure Container App — rolling restart, zero downtime
       ↓
New version live at same public URL (~5 minutes total)
```

## Project Structure

```
rag-api/
├── config.py          # Constants and logger
├── models.py          # Pydantic request/response models
├── rag.py             # RAG pipeline — load, split, embed, retrieve, generate
├── main.py            # FastAPI app, lifespan, endpoints, error handlers
├── requirements.txt   # Python dependencies
├── Dockerfile         # Production container — python:3.11-slim, non-root user
├── .dockerignore      # Excludes .env, chroma_db, uploads from image
├── data/
│   └── AI_Technical_Corpus_v1.pdf   # Pre-loaded corpus (20 AI technical paragraphs)
└── .github/
    └── workflows/
        └── deploy.yml  # GitHub Actions CI/CD pipeline
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| GROQ_API_KEY | Yes | Groq API key for LLM inference |
| CHROMA_DIR | No | ChromaDB persist directory (default: ./chroma_pdf_db) |
| TOP_K | No | Number of chunks to retrieve (default: 3) |
| CHUNK_SIZE | No | Document chunk size (default: 500) |
| CHUNK_OVERLAP | No | Chunk overlap (default: 50) |

## Production Features

| Feature | Implementation | Detail |
|---|---|---|
| RAG Pipeline | LangChain LCEL + ChromaDB | Grounded answers with source citations |
| Caching | Redis | 82x faster on repeated questions (local) |
| Rate Limiting | slowapi | 10/min on /ask, X-Forwarded-For aware |
| Error Handling | FastAPI exception handlers | 400, 422, 429, 503, 500 all covered |
| Dependency Injection | FastAPI Depends | Testable, swappable, clean separation |
| Graceful Degradation | Redis optional | API serves requests without cache if Redis unavailable |
| CI/CD | GitHub Actions | Push to main → build → deploy to Azure automatically |

## Rate Limiting

| Endpoint | Limit |
|---|---|
| POST /ask | 10/minute |
| GET /health | 60/minute |
| GET /documents | 30/minute |
| GET /cache/stats | 5/minute |
| DELETE /cache/clear | 5/minute |