"""Agente RAG con LangGraph - Versión Simple."""

import os
from typing import Any, Dict, List, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, StateGraph
from openai import OpenAI
from qdrant_client import QdrantClient

# Cargar variables de entorno
load_dotenv()

# Configuración desde .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME")
MODELO_EMBEDDING = os.getenv("MODELO_EMBEDDING", "text-embedding-3-small")
MODELO_CHAT = os.getenv("MODELO_CHAT", "gpt-4.1-mini")


# ==============================================
# ESTADO DEL AGENTE
# ==============================================
class AgentState(TypedDict):
    """Estado del agente."""
    query: str
    intent: str  # "legal_query" o "casual_conversation"
    keywords_detected: List[str]
    search_type: str
    cases: List[Any]
    response: str


# ==============================================
# CLIENTES
# ==============================================
client_openai = OpenAI(api_key=OPENAI_API_KEY)
client_qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
llm = ChatOpenAI(model=MODELO_CHAT, api_key=OPENAI_API_KEY, temperature=0.3)


# ==============================================
# FUNCIONES AUXILIARES
# ==============================================
def get_embedding(text: str) -> List[float]:
    """Genera embedding con OpenAI."""
    text = text.replace("\n", " ")
    return client_openai.embeddings.create(input=[text], model=MODELO_EMBEDDING).data[0].embedding


def detect_keywords(query: str) -> List[str]:
    """Detecta keywords técnicas en la consulta."""
    query_upper = query.upper()
    if "PIAR" in query_upper:
        return ["PIAR"]
    return []


# ==============================================
# NODOS DEL AGENTE
# ==============================================
def classify_intent(state: AgentState) -> Dict:
    """Nodo 1: Clasifica si es consulta legal o conversación casual."""
    query = state["query"]
    
    # Prompt para clasificación
    classification_prompt = f"""Clasifica la siguiente consulta del usuario en una de estas categorías:

1. "legal_query": Si es una pregunta sobre casos legales, sentencias, demandas, PIAR, tutelas, o cualquier tema jurídico
2. "casual_conversation": Si es un saludo, agradecimiento, despedida, o conversación general

CONSULTA: {query}

Responde SOLO con "legal_query" o "casual_conversation", sin explicaciones."""

    response = llm.invoke(classification_prompt)
    intent = response.content.strip().lower()
    
    # Validar respuesta
    if "legal" in intent:
        intent = "legal_query"
    elif "casual" in intent or "conversation" in intent:
        intent = "casual_conversation"
    else:
        # Por defecto, asumir que es consulta legal
        intent = "legal_query"
    
    print(f"[INTENT] Intención detectada: {intent}")
    
    # Si es consulta legal, detectar keywords
    if intent == "legal_query":
        keywords = detect_keywords(query)
        search_type = "hybrid" if keywords else "semantic"
        print(f"[SEARCH] Análisis legal: tipo={search_type}, keywords={keywords}")
        
        return {
            "intent": intent,
            "keywords_detected": keywords,
            "search_type": search_type
        }
    else:
        return {
            "intent": intent,
            "keywords_detected": [],
            "search_type": ""
        }


def search_cases(state: AgentState) -> Dict:
    """Nodo 2: Busca casos en Qdrant."""
    query_vector = get_embedding(state["query"])
    
    # Buscar en Qdrant (siempre buscar más para compensar filtrado/deduplicación)
    # Como queremos 15 casos finales:
    # - Búsqueda simple: 15 * 3 = 45
    # - Búsqueda híbrida: 15 * 20 = 300 (porque el filtrado reduce mucho)
    num_casos_finales = 15
    if state["search_type"] == "hybrid":
        limit = num_casos_finales * 20  # 300 para compensar filtrado por keywords
    else:
        limit = num_casos_finales * 3   # 45 para compensar deduplicación
    
    results = client_qdrant.query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True
    ).points
    
    # Filtrar por keywords si es búsqueda híbrida
    if state["search_type"] == "hybrid":
        filtered = []
        for hit in results:
            text = (
                str(hit.payload.get("sintesis", "")) + " " +
                str(hit.payload.get("resuelve", "")) + " " +
                str(hit.payload.get("tema", "")) + " " +
                str(hit.payload.get("texto_chunk", ""))
            ).upper()
            
            if all(kw.upper() in text for kw in state["keywords_detected"]):
                filtered.append(hit)
        results = filtered
    
    # Deduplicar por id_caso
    unique_cases = {}
    for hit in results:
        id_caso = hit.payload.get("id_caso", hit.payload.get("fila_excel"))
        if id_caso not in unique_cases:
            unique_cases[id_caso] = hit
        elif hit.score > unique_cases[id_caso].score:
            unique_cases[id_caso] = hit
    
    # Retornar siempre 15 casos únicos (o los que haya si son menos)
    cases = list(unique_cases.values())[:15]
    
    print(f"[RESULTS] Encontrados {len(cases)} casos")
    
    return {"cases": cases}


def respond_casual(state: AgentState) -> Dict:
    """Nodo 3a: Responde conversaciones casuales (sin búsqueda)."""
    query = state["query"]
    
    casual_prompt = f"""Eres un asistente legal amigable. El usuario te ha escrito algo que NO es una consulta legal.

MENSAJE DEL USUARIO: {query}

Responde de forma cordial y profesional. Si es un saludo, saluda de vuelta. Si es un agradecimiento, responde amablemente. Si pide ayuda en general, explícale brevemente que estás aquí para ayudar con consultas sobre casos legales y sentencias.

Mantén tu respuesta breve (2-3 líneas máximo)."""
    
    response = llm.invoke(casual_prompt)
    
    print(f"[RESPONSE] Respuesta casual generada")
    
    return {"response": response.content}


def generate_legal_response(state: AgentState) -> Dict:
    """Nodo 3b: Genera respuesta legal con casos encontrados."""
    if not state["cases"]:
        return {"response": "No encontré casos relevantes para tu consulta. ¿Podrías reformular tu pregunta?"}
    
    # Construir contexto
    contexto = "CASOS LEGALES RELEVANTES:\n\n"
    for i, caso in enumerate(state["cases"], 1):
        p = caso.payload
        contexto += f"--- CASO {i} ---\n"
        contexto += f"Providencia: {p.get('providencia')}\n"
        contexto += f"Tema: {p.get('tema')}\n"
        contexto += f"Síntesis: {p.get('sintesis')}\n"
        contexto += f"Sentencia: {p.get('resuelve')}\n\n"
    
    # Prompt
    prompt = f"""Eres un asesor legal. Responde en lenguaje coloquial.

PREGUNTA: {state['query']}

{contexto}

INSTRUCCIONES:
- Responde en lenguaje coloquial, como si hablaras con un amigo que NO sabe de leyes
- Evita términos jurídicos complejos (o explícalos de forma muy simple)
- Si hay varios casos, resúmelos de forma clara y estructurada
- Si preguntan por sentencias, explica qué se decidió de manera comprensible
- Si NO encuentras información relevante en los casos, dilo claramente
- Sé preciso pero comprensible
- Usa ejemplos o analogías si ayuda a la claridad

RESPUESTA:"""
    
    # Generar respuesta
    response = llm.invoke(prompt)
    
    print(f"[RESPONSE] Respuesta legal generada")
    
    return {"response": response.content}


# ==============================================
# ROUTING CONDICIONAL
# ==============================================
def route_by_intent(state: AgentState) -> str:
    """Decide el siguiente nodo según la intención."""
    if state["intent"] == "legal_query":
        return "search"
    else:
        return "respond_casual"


# ==============================================
# CONSTRUCCIÓN DEL GRAFO
# ==============================================
workflow = StateGraph(AgentState)

# Agregar nodos
workflow.add_node("classify", classify_intent)
workflow.add_node("search", search_cases)
workflow.add_node("respond_casual", respond_casual)
workflow.add_node("generate_legal", generate_legal_response)

# Definir flujo con routing condicional
workflow.set_entry_point("classify")

# Routing condicional después de clasificar
workflow.add_conditional_edges(
    "classify",
    route_by_intent,
    {
        "search": "search",
        "respond_casual": "respond_casual"
    }
)

# Flujo para consultas legales
workflow.add_edge("search", "generate_legal")
workflow.add_edge("generate_legal", END)

# Flujo para conversación casual
workflow.add_edge("respond_casual", END)

# Compilar
agent = workflow.compile()


# ==============================================
# FUNCIÓN PRINCIPAL
# ==============================================
def run_agent(query: str) -> Dict:
    """Ejecuta el agente con una consulta."""
    print(f"\n{'='*60}")
    print(f"[QUERY] Consulta: {query}")
    print(f"{'='*60}")
    
    result = agent.invoke({
        "query": query,
        "intent": "",
        "keywords_detected": [],
        "search_type": "",
        "cases": [],
        "response": ""
    })
    
    return result


# ==============================================
# PRUEBA
# ==============================================
if __name__ == "__main__":
    # Probar el agente
    result = run_agent("¿Existen casos que hablan sobre el PIAR?")
    
    print(f"\n{'='*60}")
    print(f"[OUTPUT] RESPUESTA:")
    print(f"{'='*60}")
    print(result["response"])
    print(f"\n[INFO] Casos usados: {len(result['cases'])}")

