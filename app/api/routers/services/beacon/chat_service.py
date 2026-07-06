"""
Beacon Chat Service

Main orchestrator for the Beacon chatbot.
Combines RAG, context building, and LLM to generate responses.
"""

import os
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAI

from .rag_service import RAGService
from .context_builder import ContextBuilder
from .prompts import BEACON_SYSTEM_PROMPT, QUERY_CLASSIFIER_PROMPT, RESPONSE_PROMPT


class BeaconChatService:
    """
    Main chat service for Beacon AI assistant.
    
    Orchestrates:
    1. Query classification (documentation vs user data vs out of scope)
    2. RAG retrieval for documentation context
    3. Database queries for user data context
    4. LLM response generation
    """
    
    def __init__(
        self, 
        db: AsyncSession, 
        user_id: UUID
    ):
        """
        Initialize chat service.
        
        Args:
            db: Database session for user data queries
            user_id: Current user's ID
        """
        self.db = db
        self.user_id = user_id
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        # Initialize components
        self.rag_service = RAGService()
        self.context_builder = ContextBuilder(db, user_id)
        
        # Initialize Gemini client (OpenAI-compatible API)
        self.client = OpenAI(
            api_key=self.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    
    async def _classify_query(self, query: str) -> str:
        """
        Classify the user's query to determine what context to fetch.
        
        Args:
            query: User's message
            
        Returns:
            One of: "documentation", "user_data", "both", "out_of_scope"
        """
        try:
            response = self.client.chat.completions.create(
                model="gemini-3.5-flash",
                messages=[
                    {
                        "role": "user",
                        "content": QUERY_CLASSIFIER_PROMPT.format(query=query)
                    }
                ],
                max_tokens=20,
                temperature=0
            )
            
            classification = response.choices[0].message.content.strip().lower()
            
            # Validate classification
            valid_classes = ["greeting", "documentation", "user_data", "both", "out_of_scope"]
            if classification not in valid_classes:
                # Default to both if unclear
                return "both"
            
            return classification
            
        except Exception as e:
            print(f"⚠️ Classification error: {e}")
            # Default to both on error
            return "both"
    
    def _build_history_string(self, history: List[dict]) -> str:
        """
        Convert chat history to formatted string.
        
        Args:
            history: List of {"role": "user"|"assistant", "content": str}
            
        Returns:
            Formatted history string
        """
        if not history:
            return "No previous conversation."
        
        # Only use last 6 messages for context (3 exchanges)
        recent_history = history[-6:]
        
        lines = []
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Beacon"
            lines.append(f"{role}: {msg['content']}")
        
        return "\n".join(lines)
    
    async def chat(
        self, 
        message: str, 
        history: Optional[List[dict]] = None
    ) -> str:
        """
        Process a chat message and generate a response.
        
        Args:
            message: User's message
            history: Optional conversation history
            
        Returns:
            Beacon's response
        """
        history = history or []
        
        # Step 1: Classify the query
        query_type = await self._classify_query(message)
        print(f"🔍 Query classified as: {query_type}")
        
        # Step 2: Handle greetings with a simple friendly response
        if query_type == "greeting":
            return (
                "Hey! 👋 I'm Beacon, your AssetWatch assistant. "
                "What can I help you with today?"
            )
        
        # Step 3: Handle out of scope
        if query_type == "out_of_scope":
            return (
                "I'm Beacon, your AssetWatch assistant! I specialize in helping with "
                "network monitoring - assets, monitors, metrics, and platform features. "
                "For other topics, I'd recommend checking appropriate resources. "
                "How can I help you with AssetWatch today?"
            )
        
        # Step 4: Build context based on query type
        doc_context = ""
        user_context = ""
        
        if query_type in ["documentation", "both"]:
            # Get relevant documentation from RAG
            doc_chunks = self.rag_service.search(message, k=3)
            if doc_chunks:
                doc_context = "\n\n---\n\n".join(doc_chunks)
            else:
                doc_context = "No specific documentation found for this query."
        
        if query_type in ["user_data", "both"]:
            # Get user's data context
            user_context = await self.context_builder.build_full_context()
        
        # Step 5: Build history string
        history_str = self._build_history_string(history)
        
        # Step 6: Generate response
        full_prompt = RESPONSE_PROMPT.format(
            doc_context=doc_context or "No documentation context.",
            user_context=user_context or "No user data context.",
            history=history_str,
            query=message
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gemini-3.5-flash",
                messages=[
                    {"role": "system", "content": BEACON_SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️ Response generation error: {e}")
            return (
                "I apologize, but I'm having trouble processing your request right now. "
                "Please try again in a moment."
            )
