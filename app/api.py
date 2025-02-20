import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from neo4j import GraphDatabase
import numpy as np
from openai import OpenAI, DefaultHttpxClient
from contextlib import asynccontextmanager

# Forzar que SSL_CERT_FILE esté vacío para evitar problemas con httpx/ssl.
os.environ["SSL_CERT_FILE"] = ""

# ------------------------------------------------------------------------------
# Cargar variables de entorno
# ------------------------------------------------------------------------------
load_dotenv()
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
NEO4J_URI = os.environ.get("NEO4J_URI")  # Ej: "bolt://localhost:7687" o "bolt://neo4j:7687"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
neo4j_user = "neo4j"

if not NEO4J_PASSWORD or not OPENAI_API_KEY:
    raise ValueError("Asegúrate de definir NEO4J_PASSWORD y OPENAI_API_KEY en el archivo .env")

# ------------------------------------------------------------------------------
# Crear el driver de Neo4j
# ------------------------------------------------------------------------------
driver = GraphDatabase.driver(NEO4J_URI, auth=(neo4j_user, NEO4J_PASSWORD))

# ------------------------------------------------------------------------------
# Definir el lifespan de la aplicación usando un gestor de contexto
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    driver.close()

# ------------------------------------------------------------------------------
# Crear la instancia de FastAPI con el lifespan
# ------------------------------------------------------------------------------
app = FastAPI(
    title="API RAG de Grafos",
    description="API para consultar chunks y responder preguntas sobre distintos paquetes de R (filtrado por dominio y ranking semántico).",
    version="1.0",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API RAG de Grafos"}

@app.get("/chunks", summary="Obtener nodos de tipo Chunk")
def get_chunks(limit: int = Query(10, ge=1, description="Número máximo de nodos a retornar")):
    with driver.session() as session:
        result = session.run("MATCH (c:Chunk) RETURN c LIMIT $limit", limit=limit)
        chunks = [record["c"] for record in result]
        chunks_dict = [dict(chunk) for chunk in chunks]
    return {"chunks": chunks_dict}

@app.get("/chunks/search", summary="Buscar chunks por nombre de archivo")
def search_chunks(file: str = Query(..., description="Fragmento del nombre del archivo a buscar")):
    with driver.session() as session:
        result = session.run(
            "MATCH (c:Chunk) WHERE c.file CONTAINS $file RETURN c LIMIT 10",
            file=file
        )
        chunks = [record["c"] for record in result]
        if not chunks:
            raise HTTPException(status_code=404, detail="No se encontraron chunks para el criterio de búsqueda.")
        chunks_dict = [dict(chunk) for chunk in chunks]
    return {"chunks": chunks_dict}

def cosine_similarity(vec1, vec2):
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

# ------------------------------------------------------------------------------
# Instanciar el cliente de OpenAI
# ------------------------------------------------------------------------------
openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
    http_client=DefaultHttpxClient()
)

def get_embedding_for_text(text: str, model: str = "text-embedding-ada-002") -> list:
    text_cleaned = text.replace("\n", " ")
    response = openai_client.embeddings.create(model=model, input=text_cleaned)
    embedding = response.data[0].embedding
    return embedding

# ------------------------------------------------------------------------------
# Función para determinar si la consulta está fuera del dominio
# ------------------------------------------------------------------------------
def is_off_topic(query: str, package: str) -> bool:
    # Define palabras clave relevantes para cada paquete
    keywords = {
        "faucet": ["faucet", "shiny", "plumber", "deploy", "documentation"],
        "taplock": ["taplock", "authentication", "openid", "oauth", "security", "configuration"]
    }
    query_lower = query.lower()
    relevant_keywords = keywords.get(package, [])
    # Si ninguna palabra clave está presente, consideramos que es off-topic
    return not any(keyword in query_lower for keyword in relevant_keywords)

# ------------------------------------------------------------------------------
# Endpoint para buscar chunks por similitud semántica
# ------------------------------------------------------------------------------
@app.get("/chunks/search_by_text", summary="Buscar chunks por similitud semántica")
def search_chunks_by_text(
    q: str = Query(..., description="Consulta de texto para búsqueda semántica"),
    limit: int = Query(5, ge=1, description="Número máximo de resultados a retornar")
):
    query_embedding = get_embedding_for_text(q)
    with driver.session() as session:
        result = session.run("MATCH (c:Chunk) RETURN c")
        chunks = [record["c"] for record in result]
    
    scored_chunks = []
    for chunk in chunks:
        emb = chunk.get("embedding")
        if emb is None:
            continue
        score = cosine_similarity(query_embedding, emb)
        scored_chunks.append((score, dict(chunk)))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored_chunks[:limit]
    
    return {"query": q, "results": [{"score": score, "chunk": chunk} for score, chunk in top_chunks]}

# ------------------------------------------------------------------------------
# Endpoint de chat usando RAG (filtrado por dominio y ranking semántico con fallback)
# ------------------------------------------------------------------------------
@app.post("/chat", summary="Responder preguntas utilizando RAG (filtrado por dominio)")
def chat(
    q: str = Query(..., description="Pregunta a realizar"),
    package: str = Query(..., description="Nombre del paquete (por ejemplo, faucet, taplock, etc.)"),
    limit: int = Query(5, ge=1, description="Número máximo de documentos a usar como contexto")
):
    # Configuración específica para cada paquete
    package_prompts = {
        "faucet": {
            "system_message": "Eres un experto en el paquete faucet. Responde de forma clara, detallada y concisa sobre faucet.",
            "prompt_prefix": "Utilizando la siguiente información de la documentación del paquete 'faucet':"
        },
        "taplock": {
            "system_message": "Eres un experto en el paquete taplock. Responde de forma clara y concisa sobre taplock.",
            "prompt_prefix": "Utilizando la siguiente información de la documentación del paquete 'taplock':"
        }
    }

    pkg = package.lower()
    if pkg not in package_prompts:
        raise HTTPException(status_code=400, detail=f"El paquete '{package}' no está soportado.")

    # Verificar si la consulta está fuera del dominio usando palabras clave
    if is_off_topic(q, pkg):
        return {
            "package": package,
            "query": q,
            "context": "",
            "answer": f"Lo siento, solo respondo preguntas relacionadas con el paquete {package}."
        }

    # Generar embedding para la consulta
    query_embedding = get_embedding_for_text(q)

    # Recuperar nodos del paquete especificado
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (c:Chunk) WHERE toLower(c.package) = toLower($package) RETURN c",
                package=package
            )
            chunks = [record["c"] for record in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al recuperar los chunks de Neo4j: {e}")

    # Calcular la similitud semántica y ordenar
    scored_chunks = []
    for chunk in chunks:
        emb = chunk.get("embedding")
        if emb is None:
            continue
        score = cosine_similarity(query_embedding, emb)
        scored_chunks.append((score, dict(chunk)))
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # Definir umbral de relevancia (opcional)
    threshold = 0.6
    if not scored_chunks or scored_chunks[0][0] < threshold:
        return {
            "package": package,
            "query": q,
            "context": "",
            "answer": f"Lo siento, solo respondo preguntas relacionadas con el paquete {package}."
        }

    top_chunks = scored_chunks[:limit]
    context = "\n\n".join([chunk.get("text", "") for score, chunk in top_chunks])
    if not context.strip():
        context = "No se encontró información específica en la documentación para esta consulta."

    # Construir el prompt usando la configuración del paquete
    prompt = (
        f"{package_prompts[pkg]['prompt_prefix']}\n\n"
        f"{context}\n\n"
        f"Por favor, explica detalladamente y paso a paso cómo se realiza lo siguiente:\n\n"
        f"{q}\n"
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": package_prompts[pkg]["system_message"]},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        answer = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al llamar a OpenAI: {e}")

    return {
        "package": package,
        "query": q,
        "context": context,
        "answer": answer
    }
