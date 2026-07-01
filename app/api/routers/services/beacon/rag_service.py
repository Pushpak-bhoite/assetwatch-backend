"""
Beacon RAG Service

Handles document embedding and retrieval using ChromaDB.
Stores AssetWatch documentation for context retrieval.
"""

import os
from pathlib import Path
from typing import List, Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class RAGService:
    """
    RAG (Retrieval Augmented Generation) service for Beacon.
    
    Uses ChromaDB to store and retrieve relevant documentation chunks
    based on semantic similarity to user queries.
    """
    
    _instance: Optional["RAGService"] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern - only one instance of RAG service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize RAG service with embeddings and vector store."""
        if RAGService._initialized:
            return
            
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            print("⚠️ GEMINI_API_KEY not set - RAG service will not work")
            self.vector_store = None
            return
        
        # Initialize embedding model
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=self.gemini_api_key
        )
        
        # ChromaDB persistence directory
        self.persist_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "chromadb"
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Collection name
        self.collection_name = "assetwatch_docs"
        
        # Initialize or load vector store
        self._init_vector_store()
        
        RAGService._initialized = True
        print("✅ RAG Service initialized")
    
    def _init_vector_store(self):
        """Initialize or load the vector store."""
        try:
            # Try to load existing collection
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_dir)
            )
            
            # Check if collection has documents
            collection = self.vector_store._collection
            if collection.count() == 0:
                print("📚 No documents in collection, indexing knowledge base...")
                self._index_knowledge_base()
            else:
                print(f"📚 Loaded {collection.count()} document chunks from ChromaDB")
                
        except Exception as e:
            print(f"⚠️ Error initializing vector store: {e}")
            self.vector_store = None
    
    def _index_knowledge_base(self):
        """Index the AssetWatch knowledge base documents."""
        knowledge_dir = Path(__file__).parent / "knowledge"
        
        if not knowledge_dir.exists():
            print(f"⚠️ Knowledge directory not found: {knowledge_dir}")
            return
        
        documents = []
        
        # Load all markdown files from knowledge directory
        for md_file in knowledge_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                documents.append(Document(
                    page_content=content,
                    metadata={
                        "source": md_file.name,
                        "type": "documentation"
                    }
                ))
                print(f"📄 Loaded: {md_file.name}")
            except Exception as e:
                print(f"⚠️ Error loading {md_file}: {e}")
        
        if not documents:
            print("⚠️ No documents found to index")
            return
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " "]
        )
        chunks = text_splitter.split_documents(documents)
        print(f"📝 Created {len(chunks)} chunks from {len(documents)} documents")
        
        # Add to vector store
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            persist_directory=str(self.persist_dir)
        )
        print(f"✅ Indexed {len(chunks)} chunks to ChromaDB")
    
    def search(self, query: str, k: int = 3) -> List[str]:
        """
        Search for relevant documentation chunks.
        
        Args:
            query: User's question
            k: Number of results to return
            
        Returns:
            List of relevant text chunks
        """
        if not self.vector_store:
            return []
        
        try:
            results = self.vector_store.similarity_search(query, k=k)
            return [doc.page_content for doc in results]
        except Exception as e:
            print(f"⚠️ RAG search error: {e}")
            return []
    
    def reindex(self):
        """Force reindex of knowledge base (useful after updating docs)."""
        if self.vector_store:
            # Delete existing collection
            try:
                self.vector_store.delete_collection()
            except:
                pass
        
        self._init_vector_store()
        self._index_knowledge_base()
