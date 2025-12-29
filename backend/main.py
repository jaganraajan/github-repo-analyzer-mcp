"""
FastAPI backend for MCP Demo
Handles chat requests, MCP server orchestration, and OpenAI integration
"""
import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio


from mcp_client import MCPClientManager
from openai_client import chat_with_tools


app = FastAPI(title="MCP Demo Backend")

# CORS middleware to allow Next.js frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MCP client manager
mcp_manager = MCPClientManager()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


@app.on_event("startup")
async def startup_event():
    """Initialize MCP clients on startup"""
    await mcp_manager.initialize_all()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up MCP clients on shutdown"""
    await mcp_manager.cleanup()


@app.get("/")
async def root():
    return {"message": "MCP Demo Backend API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    status = await mcp_manager.get_server_status()
    return {
        "status": "healthy",
        "mcp_servers": status
    }


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint with streaming support
    Processes chat messages, orchestrates MCP tools, and streams responses
    """
    try:
        print(f"Request: {request}")
        # Convert Pydantic models to dict format for OpenAI
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        print(f"Messages: {messages}")
        async def generate_response():
            """Generator function for streaming responses"""
            tool_calls = []
            tool_results = []
            
            try:
                async for event in chat_with_tools(
                    messages,
                    mcp_manager,
                    on_tool_call=lambda tc: tool_calls.append(tc),
                    on_tool_result=lambda tr: tool_results.append(tr)
                ):
                    print(f"Yielding event: {event.get('type', 'unknown')}")
                    yield f"data: {json.dumps(event)}\n\n"
                
                # Send completion event
                completion_event = {
                    "type": "done",
                    "toolCalls": tool_calls,
                    "toolResults": tool_results
                }
                print(f"Sending completion event with {len(tool_calls)} tool calls")
                yield f"data: {json.dumps(completion_event)}\n\n"
                
            except Exception as e:
                print(f"Error in generate_response: {e}")
                import traceback
                traceback.print_exc()
                error_event = {
                    "type": "error",
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

