import os
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# Constants
CV_DIR = os.path.join(settings.BASE_DIR, "CV")
VECTOR_STORE_PATH = os.path.join(settings.BASE_DIR, "faiss_index")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Global references to cache components
_vectors = None
_embeddings = None
_retriever = None

def get_vectors_and_embeddings():
    """
    Retrieves or initializes the embeddings and the FAISS vector store.
    """
    global _vectors, _embeddings, _retriever
    
    if _vectors is not None:
        return _vectors, _embeddings
        
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        logger.info("Initializing HuggingFaceEmbeddings model: %s...", EMBEDDING_MODEL)
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        
        # 1. Try to load local FAISS index from disk
        if Path(VECTOR_STORE_PATH).exists():
            logger.info(f"Loading existing vector store from disk at '{VECTOR_STORE_PATH}'...")
            _vectors = FAISS.load_local(
                VECTOR_STORE_PATH,
                _embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("Vector store successfully loaded from disk!")
            return _vectors, _embeddings
            
        # 2. Disk index does not exist. Let's build it!
        logger.info("No local vector store index found on disk. Building a new one...")
        docs = []
        
        # Load from CV directory if it exists and contains PDFs
        cv_path = Path(CV_DIR)
        os.makedirs(CV_DIR, exist_ok=True) # Ensure directory exists
        
        pdf_files = list(cv_path.glob("*.pdf"))
        if pdf_files:
            logger.info(f"PDF files detected in '{CV_DIR}'. Loading documents...")
            from langchain_community.document_loaders import PyPDFDirectoryLoader
            loader = PyPDFDirectoryLoader(CV_DIR)
            docs.extend(loader.load())
            logger.info(f"Loaded {len(docs)} pages from CV PDFs.")
        else:
            logger.warning(f"CV directory '{CV_DIR}' has no PDF files. Falling back to portfolio database indexing...")
            # Fallback: Index active database objects (Projects, Skills) to bootstrap the RAG index
            try:
                from portfolio.models import Project, Skill, Job
                
                # Ingest Projects
                for p in Project.objects.all():
                    content = f"Project: {p.title}. Emoji: {p.emoji}. Description: {p.description}. Tags: {p.tags}. Repository: {p.github_url}."
                    docs.append(Document(page_content=content, metadata={"source": "database_project", "id": p.id}))
                    
                # Ingest Skills
                for s in Skill.objects.all():
                    content = f"Skill: {s.name}. Category: {s.category.name}. Competency Tier: {s.tier}. Details: {s.context}."
                    docs.append(Document(page_content=content, metadata={"source": "database_skill", "id": s.id}))
                    
                # Ingest Experiences
                for j in Job.objects.all():
                    content = f"Work Experience: {j.title} at {j.company} ({j.period}). Details: {j.description}. Core Tools: {j.tags}."
                    docs.append(Document(page_content=content, metadata={"source": "database_job", "id": j.id}))
                    
                logger.info(f"Bootstrapped RAG index with {len(docs)} database entries.")
            except Exception as dbe:
                logger.error(f"Failed to load database records for vector store bootstrapping: {dbe}")
                
        # If still no documents, create a default profile index document so FAISS doesn't crash on empty input
        if not docs:
            logger.info("No source documents found. Creating default identity index document...")
            docs.append(Document(
                page_content="Portfolio Owner: Saravana Perumal R. — Generative AI Specialist, AI Engineer, and Educator.",
                metadata={"source": "default_fallback"}
            ))

        # Split documents into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        final_docs = splitter.split_documents(docs)
        
        # Build FAISS vector database
        logger.info(f"Indexing {len(final_docs)} chunks into FAISS...")
        _vectors = FAISS.from_documents(final_docs, _embeddings)
        
        # Fetch and append GitHub data if configured
        github_user = os.getenv("GITHUB_USERNAME", "saravanagithub14")
        if github_user:
            try:
                from github_connector import fetch_github_data
                github_docs = fetch_github_data(github_user)
                if github_docs:
                    logger.info("Merging GitHub repository documents into FAISS vector index...")
                    _vectors.add_documents(github_docs)
            except Exception as ghe:
                logger.error(f"Failed to fetch and merge GitHub repository documents: {ghe}", exc_info=True)
                
        # Save compiled index to disk
        _vectors.save_local(VECTOR_STORE_PATH)
        logger.info(f"FAISS vector store saved to disk at '{VECTOR_STORE_PATH}'!")
        
    except Exception as e:
        logger.error(f"Failed to initialize FAISS vector index or embeddings: {e}", exc_info=True)
        
    return _vectors, _embeddings

def get_retriever():
    """
    Returns the vector store retriever configuration.
    """
    global _retriever
    if _retriever is not None:
        return _retriever
        
    vectors, _ = get_vectors_and_embeddings()
    if vectors is not None:
        _retriever = vectors.as_retriever(search_kwargs={"k": 5})
        return _retriever
    return None

def add_document_to_index(text_content, source_name="webhook"):
    """
    Adds a new text block to the FAISS index dynamically and saves it to disk.
    """
    from langchain_core.documents import Document
    
    vectors, _ = get_vectors_and_embeddings()
    if vectors is None:
        logger.error("Cannot add document to index: Vector store not initialized.")
        return False
        
    try:
        doc = Document(
            page_content=text_content,
            metadata={"source": source_name}
        )
        vectors.add_documents([doc])
        vectors.save_local(VECTOR_STORE_PATH)
        logger.info(f"Successfully added document to FAISS vector index and saved to disk.")
        
        # Force reload retriever cache reference
        global _retriever
        _retriever = vectors.as_retriever(search_kwargs={"k": 5})
        return True
    except Exception as e:
        logger.error(f"Error occurred while adding document to index: {e}", exc_info=True)
        
    return False
