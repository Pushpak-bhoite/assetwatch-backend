"""
Beacon Chatbot API Router

Provides the chat endpoint for the Beacon AI assistant.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import User, get_db
from app.users import current_active_user
from .services.beacon import BeaconChatService


# Create router
router = APIRouter(prefix="/beacon", tags=["Beacon Chatbot"])


# ==================== REQUEST/RESPONSE MODELS ====================

class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's message")
    history: Optional[List[ChatMessage]] = Field(
        default=None, 
        max_length=20,  # Limit history to 20 messages
        description="Previous conversation messages (optional)"
    )


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    response: str = Field(..., description="Beacon's response")
    

# ==================== ENDPOINTS ====================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_beacon(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Send a message to Beacon and get a response.
    
    Beacon is an AI assistant that can:
    - Answer questions about AssetWatch features
    - Query and explain your assets, monitors, and metrics
    - Help troubleshoot monitoring issues
    
    The chat is stateless - send conversation history with each request
    if you want context from previous messages.
    
    Request Body:
        - message: Your question or message (required)
        - history: Previous messages in the conversation (optional)
        
    Returns:
        Beacon's response to your message
        
    Example:
        POST /api/beacon/chat
        {
            "message": "How many assets do I have?",
            "history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello! How can I help?"}
            ]
        }
    """
    try:
        # Initialize chat service
        chat_service = BeaconChatService(db=db, user_id=user.id)
        
        # Convert history to dict format
        history_dicts = None
        if request.history:
            history_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in request.history
            ]
        
        # Get response from Beacon
        response = await chat_service.chat(
            message=request.message,
            history=history_dicts
        )
        
        return ChatResponse(response=response)
        
    except ValueError as e:
        # API key not configured
        raise HTTPException(
            status_code=503, 
            detail="Beacon is not configured. Please set GEMINI_API_KEY."
        )
    except Exception as e:
        print(f"⚠️ Beacon error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Sorry, I encountered an error. Please try again."
        )


@router.get("/health")
async def beacon_health():
    """
    Check if Beacon service is available.
    
    Returns:
        Status of the Beacon service
    """
    import os
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    return {
        "status": "available" if api_key else "unavailable",
        "message": "Beacon is ready to help!" if api_key else "GEMINI_API_KEY not configured"
    }
