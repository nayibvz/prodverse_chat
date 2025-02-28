import os
import re
import logging
from dotenv import load_dotenv
from fastapi import HTTPException  
from neo4j import GraphDatabase
import numpy as np
from openai import OpenAI, DefaultHttpxClient
from chunking import process_all_files

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

os.environ["SSL_CERT_FILE"] = ""

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

if not OPENAI_API_KEY or not NEO4J_PASSWORD:
    raise ValueError("Asegúrate de definir OPENAI_API_KEY y NEO4J_PASSWORD en el archivo .env")

script_directory = os.path.abspath(os.path.dirname(__file__))
os.chdir(script_directory)
logger.info("Directorio de trabajo establecido en: %s", os.getcwd())

openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
    http_client=DefaultHttpxClient()
)
logger.info("Cliente de OpenAI instanciado correctamente.")

neo4j_user = "neo4j"
neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
logger.info("NEO4J_URI: %s", neo4j_uri)
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, NEO4J_PASSWORD))
logger.info("Conexión a Neo4j establecida.")

def get_embedding_for_text(text: str, model: str = "text-embedding-ada-002") -> list:
    text_cleaned = text.replace("\n", " ")
    try:
        response = openai_client.embeddings.create(model=model, input=text_cleaned)
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        logger.error("Error al generar embedding para el texto: %s", e)
        raise

def create_chunk_node(tx, file: str, chunk_id: int, text: str, embedding: list, package: str):
    query = """
    CREATE (c:Chunk {
        file: $file,
        chunk_id: $chunk_id,
        text: $text,
        embedding: $embedding,
        folder: $folder,
        package: $package
    })
    """
    tx.run(query, file=file, chunk_id=chunk_id, text=text, embedding=embedding, 
           folder=os.path.dirname(file), package=package)

def store_chunks_in_neo4j(chunks: list):
    with driver.session() as session:
        for chunk in chunks:
            logger.info("Generando embedding para %s - Chunk %s", chunk["file"], chunk["chunk_id"])
            try:
                embedding = get_embedding_for_text(chunk["text"])
                session.execute_write(
                    create_chunk_node,
                    chunk["file"],
                    chunk["chunk_id"],
                    chunk["text"],
                    embedding,
                    chunk["package"]  
                )
            except Exception as e:
                logger.error("Error procesando el chunk %s de %s: %s", chunk["chunk_id"], chunk["file"], e)
    logger.info("Todos los chunks han sido almacenados en Neo4j.")

def create_relationships():
    query = """
    MATCH (a:Chunk), (b:Chunk)
    WHERE a.file = b.file AND a.chunk_id + 1 = b.chunk_id
    MERGE (a)-[:NEXT]->(b)
    """
    with driver.session() as session:
        session.run(query)
    logger.info("Relaciones NEXT creadas entre chunks del mismo archivo.")

if __name__ == "__main__":
    try:
        logger.info("Procesando archivos para generar chunks...")
        base_directory = os.getcwd()  
        chunks_data = process_all_files(base_directory)
        logger.info("Total de chunks generados: %d", len(chunks_data))
        
        logger.info("Almacenando chunks en Neo4j...")
        store_chunks_in_neo4j(chunks_data)
        
        logger.info("Creando relaciones NEXT entre chunks...")
        create_relationships()
        
    except Exception as ex:
        logger.error("Error en el proceso de almacenamiento de embeddings: %s", ex)
    finally:
        driver.close()
