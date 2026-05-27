import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.1-8b-instant"
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_pdf_db")
TOP_K = int(os.getenv("TOP_K", "3"))
APP_VERSION = "1.0.0"
APP_TITLE = "RAG API"
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
DEFAULT_PDF_PATH = os.getenv("PDF_PATH", "./data/AI_Technical_Corpus_v1.pdf")
TEMPERATURE = int(os.getenv("TEMPERATURE", "0"))
TTL = int(os.getenv("TTL", "3600"))

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s-%(levelname)s-%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(name)