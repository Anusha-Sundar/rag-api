from config import TOP_K, get_logger,EMBEDDING_MODEL,LLM_MODEL,TEMPERATURE,CHUNK_SIZE,CHUNK_OVERLAP

from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
import shutil

logger = get_logger(__name__)

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system","""
     You are a helpful assistant who is provided with a context.
     You should only provide answers to th euser's query only if the context has informaiton about it.
     Else you should tell "I do not have information about the query".
     Strictly you should not use your own knowledge to answer questions by user which is outside the context provided to you.
     Context : {context}"""),
    ("human","{question}")
])

def load_chat_model()->any:
    return ChatGroq(model = LLM_MODEL, temperature =TEMPERATURE)

def load_embedding_model()-> any:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def document_load(filepath:str)->list:
    loader = PyPDFLoader(filepath)
    documents = loader.load()
    logger.info(f"Total of {len(documents)}  are loaded")
    return documents

def documents_split(documents:list):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"Total of {len(chunks)} chunks splitted from {len(documents)}  documents")
    return chunks    

def format_docs(docs)->any:
    return "\n\n".join(doc.page_content for doc in docs)
    
def get_retriever(vectorstore:any)->any:
    return vectorstore.as_retriever(search_kwargs={"k": TOP_K})    

def rag_chain_method(llm,vectorstore) ->tuple:
    retriever = get_retriever(vectorstore)
    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | RAG_PROMPT
        | llm
        | StrOutputParser() 
    )
    
    chain_with_src = RunnableParallel(
        answer= chain,
        sources = retriever
    )
    
    return chain_with_src,retriever

def ensure_index_exists(pdf_path: str, persist_dir: str, embedding) -> any:
    """Build index from default PDF if it doesn't exist."""
    if Path(persist_dir).exists():
        logger.info("Loading existing index")
        vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embedding
        )
    else:
        logger.info(f"Building index from {pdf_path}")
        documents = document_load(pdf_path)
        chunks = documents_split(documents)
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            persist_directory=persist_dir
        )
    logger.info(f"Index ready — {vectorstore._collection.count()} chunks")
    return vectorstore