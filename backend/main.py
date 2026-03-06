"""FastAPI main application for the agentic AI."""
import os
import uuid
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import json

from ollama_client import OllamaClient
from agent import Agent
from rag import RAGRetriever, Document


# Global instances
ollama_client: Optional[OllamaClient] = None
agent: Optional[Agent] = None
rag_retriever: Optional[RAGRetriever] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global ollama_client, agent, rag_retriever

    # Initialize on startup
    ollama_client = OllamaClient()
    rag_retriever = RAGRetriever(persist_dir="./data/chroma_db")
    agent = Agent(ollama_client, rag_retriever)

    print("Agent initialized successfully!")
    yield

    # Cleanup on shutdown
    print("Shutting down...")


app = FastAPI(
    title="Local Agentic AI",
    description="A local agentic AI powered by Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for external access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    stream: bool = True


class ChatResponse(BaseModel):
    response: str
    done: bool


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool


# Endpoints
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Check API and Ollama health."""
    ollama_ok = await ollama_client.health_check() if ollama_client else False
    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama_connected=ollama_ok
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with streaming support."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    if request.stream:
        async def generate():
            thinking_notified = False
            has_content = False
            async for chunk in agent.run(request.message, history, stream=True):
                if chunk:
                    has_content = True
                    yield {
                        "event": "message",
                        "data": json.dumps({"content": chunk, "done": False})
                    }
                elif not thinking_notified:
                    # First empty chunk means model is thinking
                    thinking_notified = True
                    yield {
                        "event": "thinking",
                        "data": json.dumps({"status": "thinking"})
                    }
            yield {
                "event": "message",
                "data": json.dumps({"content": "", "done": True})
            }

        return EventSourceResponse(generate())
    else:
        response = await agent.run_sync(request.message, history)
        return ChatResponse(response=response, done=True)


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for RAG."""
    if not rag_retriever:
        raise HTTPException(status_code=503, detail="RAG not initialized")

    try:
        content = await file.read()
        text = content.decode("utf-8")

        doc = Document(
            id=str(uuid.uuid4()),
            content=text,
            metadata={"filename": file.filename}
        )

        await rag_retriever.add_documents([doc])

        return {"status": "success", "document_id": doc.id, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/documents/count")
async def document_count():
    """Get document count."""
    if not rag_retriever:
        raise HTTPException(status_code=503, detail="RAG not initialized")

    count = await rag_retriever.get_document_count()
    return {"count": count}


@app.post("/api/documents/search")
async def search_documents(query: str, top_k: int = 5):
    """Search documents."""
    if not rag_retriever:
        raise HTTPException(status_code=503, detail="RAG not initialized")

    results = await rag_retriever.search(query, top_k)
    return {"results": results}


@app.get("/api/images/{filename}")
async def get_image(filename: str):
    """Serve generated images."""
    import os
    filepath = f"/tmp/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath, media_type="image/png")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
