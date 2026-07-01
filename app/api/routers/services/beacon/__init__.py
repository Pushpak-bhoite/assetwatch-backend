"""
Beacon Chatbot Service

AI-powered assistant for AssetWatch that can:
- Answer questions about AssetWatch features
- Query user's assets, monitors, and metrics
- Provide helpful guidance on using the platform

Components:
- chat_service: Main chat orchestration
- rag_service: ChromaDB vector store for documentation
- context_builder: Build context from user's database
- prompts: System prompts for the LLM
"""

from .chat_service import BeaconChatService
from .rag_service import RAGService
from .context_builder import ContextBuilder

__all__ = ["BeaconChatService", "RAGService", "ContextBuilder"]
