## Configuración Inicial

**1. Configurar credenciales:**

```
Configurar el .env con las variables correspondientes
```

**2. Instalar dependencias:**
```bash
pip install -r requirements.txt
```

## Uso

### 1. Probar el Agente Directamente

```bash
python -m src.agent
```

### 2. Iniciar API

```bash
python -m src.api
```

La API estará en http://localhost:8000

### 3. Usar la API

**Desde el navegador:**
- Abre http://localhost:8000/docs

**Consulta Legal:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Existen casos sobre el PIAR?"}'
```

**Conversación Casual:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hola, ¿cómo estás?"}'
```

**Con Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={"query": "¿Existen casos sobre el PIAR?"}
)

print(response.json()["response"])
```

## Cómo Funciona

### Agente LangGraph (Inteligente)

```
START → classify_intent
         ↓
         ├─ legal_query → search_cases → generate_legal → END
         │
         └─ casual_conversation → respond_casual → END
```

1. **classify_intent**: Detecta si es consulta legal o conversación casual
2. **Flujo Legal**: 
   - search_cases: Busca en Qdrant (semántica o híbrida)
   - generate_legal: Genera respuesta con casos encontrados
3. **Flujo Casual**:
   - respond_casual: Responde cordialmente sin buscar en Qdrant

### Detección Inteligente

**Conversación Casual:**
- "Hola", "Gracias", "Adiós" → Responde sin buscar en Qdrant
- Respuestas cordiales y breves

**Consultas Legales:**
- "¿Casos sobre PIAR?", "Sentencias de tutela" → Busca en Qdrant
- Si detecta términos técnicos (PIAR, etc.):
  - Búsqueda híbrida (semántica + keyword)
  - Filtra por keyword en síntesis, resuelve y tema
  - Retorna 15 casos únicos

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Info básica |
| `/health` | GET | Health check |
| `/chat` | POST | Consulta con respuesta |
| `/docs` | GET | Documentación interactiva |

## Ejemplos de Consultas

### Conversación Casual (No busca en Qdrant):
- "Hola"
- "Gracias por tu ayuda"
- "¿Qué puedes hacer?"
- "Adiós"

**Respuesta esperada:**
```json
{
  "response": "¡Hola! Soy tu asistente legal...",
  "intent": "casual_conversation",
  "num_cases": 0,
  "search_type": ""
}
```

### Consultas Legales (Busca en Qdrant):
- "¿Existen casos sobre el PIAR?"
- "¿Cuáles son las sentencias de demandas por redes sociales?"
- "Casos de acoso escolar"
- "¿Qué dice la jurisprudencia sobre tutela?"

**Respuesta esperada:**
```json
{
  "response": "Encontré 2 casos sobre PIAR...",
  "intent": "legal_query",
  "num_cases": 15,
  "search_type": "hybrid"
}
```


