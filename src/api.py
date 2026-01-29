"""API REST con FastAPI - Versión Simple."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent import run_agent

# Cargar variables de entorno
load_dotenv()
API_PORT = int(os.getenv("API_PORT", 8000))

# ==============================================
# CREAR APP
# ==============================================
app = FastAPI(
    title="Legal RAG Assistant",
    version="1.0.0",
    description="Sistema RAG para consultas legales"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================
# MODELOS
# ==============================================
class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str
    intent: str  # "legal_query" o "casual_conversation"
    num_cases: int
    search_type: str


# ==============================================
# ENDPOINTS
# ==============================================
@app.get("/")
def root():
    """Raíz - redirige a docs."""
    return {"message": "API funcionando. Ve a /docs para la documentación"}


@app.get("/health")
def health():
    """Health check."""
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Endpoint principal de chat.
    
    Ejemplo:
    ```json
    {
        "query": "¿Existen casos sobre el PIAR?"
    }
    ```
    """
    # Ejecutar agente
    result = run_agent(request.query)
    
    return ChatResponse(
        response=result["response"],
        intent=result.get("intent", "unknown"),
        num_cases=len(result.get("cases", [])),
        search_type=result.get("search_type", "")
    )


# ==============================================
# EJECUTAR
# ==============================================
if __name__ == "__main__":
    import uvicorn
    
    print("Legal RAG Assistant")
    print("="*60)
    print(f"[SERVER] Servidor iniciando en http://localhost:{API_PORT}")
    print(f"[DOCS] Documentación en http://localhost:{API_PORT}/docs")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)

