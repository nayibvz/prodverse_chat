import os
import re
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Cambiar el directorio de trabajo al directorio donde se encuentra este script
script_directory = os.path.abspath(os.path.dirname(__file__))
os.chdir(script_directory)
logger.info("Directorio de trabajo establecido en: %s", os.getcwd())

def chunk_text(text: str, max_words: int = 200, overlap: int = 50) -> list:
    """
    Divide el texto en chunks basados en párrafos y agrupa párrafos completos
    para preservar el contexto semántico.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""
    current_count = 0

    for paragraph in paragraphs:
        words = paragraph.split()
        para_word_count = len(words)
        if current_count + para_word_count > max_words and current_chunk:
            chunks.append(current_chunk.strip())
            # Reiniciar el chunk utilizando las últimas palabras (solapamiento)
            overlap_words = current_chunk.split()[-overlap:] if overlap < current_count else current_chunk.split()
            current_chunk = " ".join(overlap_words) + " " + paragraph + " "
            current_count = len(overlap_words) + para_word_count
        else:
            current_chunk += paragraph + " "
            current_count += para_word_count
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def chunk_code(text: str, max_lines: int = 50, overlap: int = 5) -> list:
    """
    Divide el código en chunks de aproximadamente 'max_lines' líneas,
    utilizando una ventana deslizante con solapamiento para mantener el contexto.
    """
    lines = text.splitlines()
    chunks = []
    start = 0
    while start < len(lines):
        chunk_lines = lines[start:start+max_lines]
        chunk = "\n".join(chunk_lines)
        chunks.append(chunk)
        start += max_lines - overlap
    return chunks

def process_file(file_path: str) -> list:
    """
    Abre el archivo y decide el método de chunking basado en la extensión o el nombre del archivo.
    Retorna una lista de chunks.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error("Error al leer %s: %s", file_path, e)
        return []
    
    file_name = os.path.basename(file_path)
    _, ext = os.path.splitext(file_name.lower())
    
    if ext in [".md", ".qmd"]:
        return chunk_text(content, max_words=200, overlap=50)
    elif ext in [".r"]:
        return chunk_code(content, max_lines=30, overlap=5)
    elif file_name in ["Dockerfile", "entrypoint.R", "app.R", "plumber.R"]:
        return chunk_code(content, max_lines=30, overlap=5)
    else:
        return chunk_text(content, max_words=200, overlap=50)

def process_all_files(base_directory: str):
    """
    Recorre recursivamente la carpeta 'source' y procesa los archivos de cada subdirectorio 
    (cada paquete). Retorna una lista de diccionarios con metadatos y el chunk generado.
    """
    all_chunks = []
    source_dir = os.path.join(base_directory, "source")
    if not os.path.exists(source_dir):
        logger.error("La carpeta 'source' no existe en %s", base_directory)
        return all_chunks

    # Iterar sobre cada paquete dentro de 'source'
    for package in os.listdir(source_dir):
        package_path = os.path.join(source_dir, package)
        if not os.path.isdir(package_path):
            continue
        logger.info("Procesando paquete: %s", package)
        # Para faucet, se procesan solo directorios que contengan "docs" o "examples".
        for root, dirs, files in os.walk(package_path):
            if package.lower() == "faucet" and not any(x in root for x in ["docs", "examples"]):
                continue
            # Para otros paquetes (ej. taplock), procesamos todos los archivos.
            folder = os.path.relpath(root, package_path)
            for file in files:
                file_path = os.path.join(root, file)
                chunks = process_file(file_path)
                logger.info("Procesado %s: %d chunks generados.", file_path, len(chunks))
                for idx, chunk in enumerate(chunks):
                    all_chunks.append({
                        "package": package,  # Asignar el nombre del paquete
                        "file": file_path,
                        "folder": folder,
                        "chunk_id": idx,
                        "text": chunk
                    })
    return all_chunks

if __name__ == "__main__":
    base_directory = os.getcwd()  # Asumiendo que ejecutas este script en la raíz
    chunks_data = process_all_files(base_directory)
    logger.info("Total de chunks generados: %d", len(chunks_data))
