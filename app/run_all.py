import os
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
if not NEO4J_PASSWORD:
    logger.error("Asegúrate de definir NEO4J_PASSWORD en el archivo .env")
    exit(1)

neo4j_user = "neo4j"

driver = GraphDatabase.driver(NEO4J_URI, auth=(neo4j_user, NEO4J_PASSWORD))

base_directory = os.getcwd()
source_dir = os.path.join(base_directory, "source")
if not os.path.exists(source_dir) or not os.listdir(source_dir):
    logger.info("La carpeta 'source' no existe o está vacía. Iniciando descarga de archivos...")
    try:
        import download_packages
        download_packages.main()
        logger.info("Descarga de archivos completada.")
    except Exception as e:
        logger.error("Error en la descarga de archivos: %s", e)
        exit(1)
else:
    logger.info("Archivos ya descargados en la carpeta 'source'.")

try:
    import chunking
    chunks_data = chunking.process_all_files(base_directory)
    logger.info("Total de chunks generados: %d", len(chunks_data))
except Exception as e:
    logger.error("Error al procesar archivos (chunking): %s", e)
    exit(1)

try:
    with driver.session() as session:
        result = session.run("MATCH (c:Chunk) RETURN count(c) AS count")
        record = result.single()
        node_count = record["count"] if record else 0
        if node_count > 0:
            logger.info("La base de datos ya contiene %d nodos (Chunk). Se omite el almacenamiento.", node_count)
        else:
            logger.info("No se encontraron nodos en la base de datos. Iniciando almacenamiento de embeddings...")
            import store_embedding
            store_embedding.store_chunks_in_neo4j(chunks_data)
            store_embedding.create_relationships()
            logger.info("Embeddings y relaciones almacenados en Neo4j.")
except Exception as e:
    logger.error("Error en el almacenamiento de embeddings en Neo4j: %s", e)
    exit(1)

driver.close()

logger.info("Proceso completo.")
