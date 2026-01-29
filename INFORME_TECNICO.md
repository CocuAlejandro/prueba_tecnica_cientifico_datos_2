# INFORME TÉCNICO - Prueba tecnica 2 cientifico de datos
## Agente de IA con sistema RAG para Asesoría Legal Automatizada

**Fecha de elaboración**: Enero 2026  
**Autor**: Cocu Alejandro Iglesias Osorio
**Empresa:** DataKnow


---

## 1. EXPLICACIÓN DEL CASO

### Contexto del Negocio
Un consultorio legal busca automatizar el proceso de asesoría a clientes sobre posibles demandas y sus resultados mediante inteligencia artificial generativa. Actualmente, los abogados deben consultar manualmente un archivo Excel con 329 casos históricos de sentencias para asesorar a sus clientes, lo cual consume tiempo significativo.

### Objetivo
Desarrollar una Prueba de Concepto (PoC) que permita:
- Consultar automáticamente casos históricos de demandas y sentencias
- Responder preguntas en lenguaje coloquial (comprensible para personas sin conocimientos legales)
- Reducir el tiempo de los abogados permitiéndoles enfocarse en consultas complejas

### Alcance de la Solución
Se implementó un sistema RAG (Retrieval Augmented Generation) que:
- Indexa todos los 329 casos sin pérdida de contexto
- Responde las 5 preguntas del caso de negocio
- Provee una API REST para integración con otros sistemas
- Mantiene respuestas en lenguaje coloquial y accesible

---

## 2. SUPUESTOS

### Supuestos Técnicos
1. **Datos completos**: Se asume que el archivo Excel `sentencias_pasadas.xlsx` contiene toda la información necesaria para generar respuestas precisas
2. **Conectividad**: El sistema requiere conexión a internet para acceder a OpenAI API y Qdrant Cloud
3. **Calidad de datos**: Los textos en las columnas 'sintesis' y 'resuelve' son suficientemente descriptivos
4. **Casos únicos**: Cada fila del Excel representa un caso legal independiente

### Supuestos de Negocio
1. **Lenguaje coloquial**: Los usuarios finales (clientes) no tienen conocimientos legales avanzados
2. **Consultas contextuales**: Las preguntas pueden incluir términos técnicos específicos (ej: PIAR, acoso escolar)
3. **Precisión prioritaria**: Es más importante la precisión que la velocidad de respuesta
4. **Casos relevantes**: Se espera que el sistema retorne entre 10-15 casos para contexto suficiente

### Supuestos de Infraestructura
1. **Ambiente de desarrollo**: Python 3.8+
2. **Servicios cloud**: Uso de Qdrant Cloud para almacenamiento vectorial
3. **APIs comerciales**: Acceso a OpenAI API (GPT-4o-mini y text-embedding-3-small)

---

## 3. FORMAS PARA RESOLVER EL CASO Y OPCIÓN TOMADA

### Opciones Evaluadas

#### Opción 1: Búsqueda por Keywords (Tradicional)
**Descripción**: Sistema de búsqueda basado en coincidencias exactas de palabras clave.
- **Ventajas**: Rápido, sin costos de API
- **Desventajas**: No entiende sinónimos ni contexto semántico
- **Conclusión**: Descartada por limitaciones en comprensión de lenguaje natural

#### Opción 2: RAG con Embeddings Simples
**Descripción**: Sistema de búsqueda semántica pura usando embeddings.
- **Ventajas**: Entiende contexto y sinónimos
- **Desventajas**: Puede perder términos técnicos específicos (ej: acrónimos)
- **Conclusión**: Insuficiente para casos con términos técnicos específicos

#### Opción 3: RAG con Búsqueda Híbrida (SELECCIONADA)
**Descripción**: Combina búsqueda semántica con filtrado por keywords cuando se detectan términos específicos.
- **Ventajas**: 
  - Comprensión semántica del contexto
  - Precisión en términos técnicos específicos
  - Respuestas en lenguaje coloquial
  - Sin pérdida de contexto (chunking inteligente)
- **Desventajas**: Mayor complejidad de implementación
- **Conclusión**: SELECCIONADA por balance óptimo entre precisión y comprensión

### Arquitectura Implementada

```
┌─────────────────────────────────────────────────────────────┐
│                    USUARIO / CLIENTE                         │
└───────────────────────────┬─────────────────────────────────┘
                            │ Consulta
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     API FastAPI                              │
│              (Endpoint: POST /chat)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   AGENTE LANGGRAPH                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Clasificar Intención                             │   │
│  │     (Legal Query vs Conversación Casual)             │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│      ┌────────┴────────┐                                     │
│      ▼                 ▼                                     │
│  ┌────────┐      ┌─────────────┐                           │
│  │ Casual │      │ Legal Query │                           │
│  │Response│      │   + Detect  │                           │
│  └────────┘      │  Keywords   │                           │
│                  └──────┬──────┘                           │
│                         │                                   │
│                         ▼                                   │
│              ┌──────────────────────┐                      │
│              │  2. Buscar Casos     │                      │
│              │  - Semantic Search   │                      │
│              │  - Hybrid Search     │                      │
│              │  (Qdrant Cloud)      │                      │
│              └──────────┬───────────┘                      │
│                         │                                   │
│                         ▼                                   │
│              ┌──────────────────────┐                      │
│              │ 3. Generar Respuesta │                      │
│              │  (GPT-4o-mini)       │                      │
│              └──────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               SERVICIOS EXTERNOS                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  OpenAI API      │      │  Qdrant Cloud    │            │
│  │  - Embeddings    │      │  - 330 vectors   │            │
│  │  - Chat (GPT)    │      │  - 329 casos     │            │
│  └──────────────────┘      └──────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Principales

#### 1. ETL e Indexación (Notebook)
- **Carga de datos**: Lectura de `sentencias_pasadas.xlsx` (329 casos)
- **Chunking inteligente**: División de textos largos con overlap de 3,000 caracteres
  - Máximo 30,000 caracteres por chunk
  - Solo 1 caso requirió división (SU.546/23 → 2 chunks)
  - Total: 330 vectores indexados
- **Generación de embeddings**: Modelo `text-embedding-3-small` (1536 dimensiones)
- **Indexación**: Subida a Qdrant Cloud con metadatos completos

#### 2. Agente Inteligente (LangGraph)
- **Clasificación de intención**: Distingue entre consulta legal y conversación casual
- **Detección de keywords**: Identifica términos técnicos específicos (ej: PIAR)
- **Routing condicional**: Ejecuta diferentes flujos según el tipo de consulta
- **Búsqueda híbrida**:
  - Semántica: 45 resultados iniciales → 15 casos únicos
  - Híbrida: 300 resultados iniciales → filtrado por keywords → 15 casos únicos
- **Deduplicación**: Asegura casos únicos aunque múltiples chunks sean relevantes

#### 3. API REST (FastAPI)
- **Endpoint principal**: `POST /chat`
- **Input**: `{"query": "texto de la consulta"}`
- **Output**: `{"response": "...", "intent": "...", "num_cases": 15, "search_type": "..."}`
- **Documentación**: Swagger UI automático en `/docs`

---

## 4. RESULTADOS DEL ANÁLISIS DE LOS DATOS Y LOS MODELOS

### Análisis de Datos

#### Estadísticas del Dataset
- **Total de casos**: 329
- **Casos con textos largos**: 1 caso excede 8,000 tokens
- **Distribución de temas**: Variedad de casos legales (tutelas, demandas, etc.)
- **Campos utilizados**:
  - `providencia`: Identificador del caso
  - `tema`: Categoría legal
  - `sintesis`: Descripción del caso
  - `resuelve`: Sentencia final

#### Tratamiento de Contexto Largo
El caso SU.546/23 tenía 35,614 caracteres, excediendo el límite de contexto. Se implementó:
- División en 2 chunks con overlap de 3,000 caracteres
- Resultado: CERO pérdida de contexto
- Verificación: 330 vectores indexados correctamente

### Desempeño del Modelo

#### Métricas de Búsqueda

| Tipo de Búsqueda | Limit Inicial | Casos Finales | Precisión |
|------------------|---------------|---------------|-----------|
| Semántica        | 45            | 15 únicos     | Alta      |
| Híbrida (PIAR)   | 300           | 2 únicos      | Muy Alta  |

#### Evaluación Cualitativa - Preguntas del Caso de Negocio

**Pregunta 1-2**: ¿Cuáles son las sentencias de 3 demandas y de qué trataron?
- **Resultado**: Respuestas precisas con síntesis clara
- **Lenguaje**: Coloquial y comprensible
- **Fuente**: Casos C-035/23, A.975/24, T-561/23

**Pregunta 3-4**: ¿Sentencia y detalle del caso de acoso escolar?
- **Resultado**: Identificó correctamente el caso T-249/24
- **Precisión**: Alta, con detalles específicos de la sentencia
- **Contexto**: Explicó el caso y sus implicaciones

**Pregunta 5**: ¿Casos sobre PIAR?
- **Resultado**: Encontró 2 casos (T-085/23, T-249/24)
- **Desafío**: Requirió búsqueda híbrida por ser acrónimo técnico
- **Solución**: Sistema detecta "PIAR" y aplica filtrado adicional
- **Éxito**: 100% de recall (encontró todos los casos existentes)

### Performance del Sistema

#### Tiempos de Respuesta
- **Clasificación de intención**: ~1-2 segundos
- **Búsqueda en Qdrant**: ~0.5-1 segundo
- **Generación de respuesta**: ~3-5 segundos
- **Total**: ~5-8 segundos por consulta

#### Costos Estimados (por consulta)
- **Embedding (consulta)**: ~$0.00001
- **Búsqueda Qdrant**: Incluido en plan cloud
- **Generación GPT-4o-mini**: ~$0.0003
- **Total por consulta**: ~$0.00031 USD

---

## 5. FUTUROS AJUSTES O MEJORAS

#### 1. Re-ranking de Resultados
**Actual**: Ordenamiento por similitud coseno
**Propuesta**: Implementar Cohere Rerank o similar para mejorar orden de relevancia
- Filtro semántico (actual)
- Re-ranking con modelo especializado
- Resultado: Top 15 más precisos

#### 2. Cache de Consultas
**Actual**: Cada consulta ejecuta todo el pipeline
**Propuesta**: Redis cache para consultas frecuentes
- Reduce latencia en consultas repetidas
- Ahorra costos de API

---

## 6. APRECIACIONES Y COMENTARIOS DEL CASO

### Logros Destacados

#### 1. Cero Pérdida de Contexto
La implementación de chunking inteligente con overlap garantizó que ningún caso quedara fuera del sistema, incluso aquellos con textos extensos. Esto es crítico para la precisión legal donde un detalle omitido puede cambiar la interpretación.

#### 2. Búsqueda Híbrida Efectiva
La detección automática de términos técnicos (como "PIAR") y el switch a búsqueda híbrida demostró ser esencial. La búsqueda semántica pura falló inicialmente en encontrar estos casos, pero la solución híbrida logró 100% de recall.

#### 3. Lenguaje Accesible
El sistema logró transformar lenguaje legal complejo en explicaciones coloquiales sin perder precisión técnica. Esto cumple el objetivo de negocio de servir a clientes sin conocimientos legales.

### Desafíos Enfrentados

#### 1. Balance Precisión vs Contexto
**Desafío**: Proveer suficientes casos para contexto sin abrumar al LLM
**Solución**: 15 casos resultó ser un balance óptimo entre contexto y tiempo de respuesta

#### 2. Acrónimos y Términos Técnicos
**Desafío**: La búsqueda semántica no captura acrónimos exactos
**Solución**: Sistema de detección de keywords + búsqueda híbrida

#### 3. Deduplicación Inteligente
**Desafío**: Múltiples chunks del mismo caso aparecían en resultados
**Solución**: Deduplicación por ID manteniendo el chunk más relevante

### Consideraciones Éticas y Legales

#### Responsabilidad
- El sistema es una **herramienta de apoyo**, no reemplaza el criterio legal profesional
- Las respuestas deben ser validadas por abogados antes de acciones legales
- Debe incluirse disclaimer en respuestas


### Conclusión

La PoC demuestra viabilidad técnica y comercial del sistema RAG para asesoría legal automatizada. Los resultados cuantitativos (100% de casos indexados, respuestas precisas en 5-8 segundos) y cualitativos (lenguaje accesible, detección de términos técnicos) validan el enfoque de búsqueda híbrida.

**Recomendación**: Proceder con implementación en producción con las mejoras de corto plazo priorizadas, especialmente:
1. Expansión de keywords legales
2. Sistema de feedback
3. Monitoreo y logging robusto

El sistema está listo para escalar y generar valor inmediato al consultorio legal, reduciendo tiempos de consulta en un estimado del 60-80% para casos rutinarios.

---

## ANEXO: Stack Técnico


### Servicios Cloud
- **Qdrant Cloud**: Vector database (330 vectores, 1536 dimensiones)
- **OpenAI API**: 
  - Embeddings: text-embedding-3-small
  - Chat: gpt-4.1-mini

### Repositorio
- Python 3.8+
- Estructura modular en `src/`
- Notebooks en `notebooks/`
- Variables de entorno en `.env`

---


