"""
Vector Store - Fixed validation for Pinecone API keys with underscores
"""

import os
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore


_EMBEDDINGS = None
_VECTORSTORE = None


def get_embeddings():
    """Get or create OpenAI embeddings instance"""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY missing from .env")
        _EMBEDDINGS = OpenAIEmbeddings(api_key=openai_key)
    return _EMBEDDINGS


def get_vectorstore():
    """
    Get or create Pinecone vector store.
    
    IMPORTANT: Requires PINECONE_API_KEY environment variable.
    langchain-pinecone reads it automatically.
    """
    global _VECTORSTORE
    if _VECTORSTORE is None:
        # Check if Pinecone API key exists
        pinecone_key = os.getenv("PINECONE_API_KEY")
        if not pinecone_key:
            raise RuntimeError(
                "PINECONE_API_KEY missing from .env file. "
                "Get your key from https://app.pinecone.io"
            )
        
        index_name = os.getenv("PINECONE_INDEX", "chatbot-index")
        
        try:
            # PineconeVectorStore automatically reads PINECONE_API_KEY from env
            _VECTORSTORE = PineconeVectorStore(
                index_name=index_name,
                embedding=get_embeddings(),
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Pinecone index '{index_name}'. "
                f"Error: {e}"
            )
    
    return _VECTORSTORE


# ============================================================
# CHATBASE-LIKE VECTOR MANAGEMENT
# ============================================================

def replace_document_vectors(
    *,
    bot_id: str,
    doc_db_id: str,
    documents: List,
):
    """
    Chatbase-like behavior:
    - Delete ALL old vectors for this document
    - Insert new vectors with stable IDs

    Vector ID format:
        bot_id:doc_db_id:chunk_index
    """

    vs = get_vectorstore()

    # Delete old vectors for this document
    try:
        vs._index.delete(
            filter={
                "bot_id": bot_id,
                "doc_db_id": doc_db_id,
            }
        )
    except Exception as e:
        # If delete fails, log but continue (maybe no old vectors)
        print(f"Warning: Could not delete old vectors: {e}")

    # Upsert new vectors with stable IDs
    ids = [
        f"{bot_id}:{doc_db_id}:{i}"
        for i in range(len(documents))
    ]

    vs.add_documents(documents, ids=ids)