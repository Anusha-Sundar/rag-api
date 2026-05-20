# RAG API

A production-grade Retrieval Augmented Generation API built with 
LangChain, ChromaDB, and FastAPI. Deployed on Azure Container Apps.

## Live Demo
Base URL: https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io
Swagger UI: https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io/docs

## Architecture
User → POST /ask → FastAPI → ChromaDB (vector search) → Groq LLM → Answer + Sources

[diagram here]

## Tech Stack
- FastAPI — async REST API
- LangChain — RAG pipeline orchestration  
- ChromaDB — vector store for document embeddings
- sentence-transformers/all-MiniLM-L6-v2 — embedding model
- Groq (llama-3.1-8b-instant) — LLM
- Docker — containerisation
- Azure Container Registry — image storage
- Azure Container Apps — serverless deployment
- GitHub Actions — CI/CD pipeline

## API Endpoints
GET  /health — service status and document count
POST /ask    — ask a question, get grounded answer with sources
GET  /docs   — interactive Swagger UI

## Example Usage
curl -X POST https://rag-api.happyforest-2eae1650.eastus.azurecontainerapps.io/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "top_k": 3}'

## Local Development
docker build -t rag-api:latest .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key rag-api:latest

## CI/CD
Push to main → GitHub Actions builds AMD64 image → pushes to ACR → 
deploys to Container Apps automatically.