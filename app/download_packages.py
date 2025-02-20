import os
import time
import logging
from github import Github, GithubException
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Cargar variables de entorno y token de GitHub
load_dotenv()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    logger.error("Asegúrate de definir GITHUB_TOKEN en el archivo .env")
    exit(1)

# Cambiar el directorio de trabajo al directorio donde se encuentra este script
script_directory = os.path.abspath(os.path.dirname(__file__))
os.chdir(script_directory)
logger.info("Directorio de trabajo establecido a: %s", os.getcwd())

# Configurar autenticación de GitHub
g = Github(GITHUB_TOKEN)

# Configuración de paquetes: define para cada paquete el repositorio y las rutas de interés.
packages_config: Dict[str, Dict] = {
    "faucet": {
        "repo": "ixpantia/faucet",
        "paths": {
            "docs/en": {"exts": [".md"], "allowed_filenames": None},
            "docs/es": {"exts": [".md"], "allowed_filenames": None},
            "examples/plumber_in_packages": {"exts": None, "allowed_filenames": ["Dockerfile", "entrypoint.R"]},
            "examples/quarto": {"exts": [".qmd"], "allowed_filenames": None},
            "examples/shiny-docker-renv": {"exts": None, "allowed_filenames": None},
            "examples/shiny": {"exts": None, "allowed_filenames": ["app.R"]},
            "examples/simple": {"exts": None, "allowed_filenames": ["plumber.R"]}
        }
    },
    "taplock": {
        "repo": "ixpantia/taplock",
        "paths": {
            "docs": {"exts": [".md"], "allowed_filenames": None},
            "example": {"exts": None, "allowed_filenames": None},
            "man": {"exts": None, "allowed_filenames": None},
            # Por ejemplo, para obtener solo el README:
            "": {"exts": None, "allowed_filenames": ["README.md"]}
        }
    }
}

def download_files_recursive(
    repo,  # Repositorio de PyGithub
    github_path: str,
    local_base: str,
    exts: Optional[List[str]] = None,
    allowed_filenames: Optional[List[str]] = None,
    max_retries: int = 3,
    backoff_factor: int = 10,
    delay_between_requests: float = 1.0  # 1 segundo de espera entre solicitudes
) -> None:
    """
    Descarga recursivamente el contenido de 'github_path' del repositorio, 
    guardándolo en 'local_base/github_path'. Se filtran archivos por extensión y nombre.
    Implementa reintentos con backoff en caso de exceder el límite de tasa.
    """
    try:
        contents = repo.get_contents(github_path)
    except GithubException as e:
        if e.status == 404:
            logger.warning("Ruta no encontrada: %s. Se omite.", github_path)
            return
        else:
            raise

    for content_file in contents:
        # Introducir un retardo entre solicitudes para disminuir la tasa de peticiones
        time.sleep(delay_between_requests)
        
        if content_file.type == "dir":
            download_files_recursive(
                repo=repo,
                github_path=content_file.path,
                local_base=local_base,
                exts=exts,
                allowed_filenames=allowed_filenames,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                delay_between_requests=delay_between_requests
            )
        else:
            file_name = os.path.basename(content_file.path)
            if exts is not None:
                _, extension = os.path.splitext(file_name.lower())
                if extension not in exts:
                    continue
            if allowed_filenames is not None:
                if file_name not in allowed_filenames:
                    continue

            retries = 0
            current_backoff = backoff_factor
            while retries < max_retries:
                try:
                    file_data = content_file.decoded_content
                    break
                except GithubException as e:
                    if e.status == 403:
                        logger.warning("Límite de tasa excedido para %s. Reintentando en %d segundos...", content_file.path, current_backoff)
                        time.sleep(current_backoff)
                        retries += 1
                        current_backoff *= 2
                    else:
                        logger.error("Error al obtener el contenido de %s: %s", content_file.path, e)
                        file_data = None
                        break

            if file_data is None:
                logger.error("No se pudo descargar %s después de %d reintentos.", content_file.path, max_retries)
                continue

            local_path = os.path.join(local_base, content_file.path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            try:
                text_data = file_data.decode("utf-8")
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(text_data)
                logger.info("[Texto] Descargado: %s -> %s", content_file.path, local_path)
            except Exception as e:
                try:
                    with open(local_path, "wb") as f:
                        f.write(file_data)
                    logger.info("[Binario] Descargado: %s -> %s", content_file.path, local_path)
                except Exception as ex:
                    logger.error("Error al guardar %s: %s", content_file.path, ex)

def download_package(package: str, config: Dict):
    """
    Descarga los archivos para un paquete según la configuración.
    Los archivos se guardarán en 'source/<package>'.
    """
    repo = g.get_repo(config["repo"])
    local_base = os.path.join("source", package)
    os.makedirs(local_base, exist_ok=True)
    
    for github_path, filters in config["paths"].items():
        exts = filters.get("exts")
        allowed_filenames = filters.get("allowed_filenames")
        logger.info("Descargando %s para el paquete %s...", github_path, package)
        try:
            download_files_recursive(repo, github_path, local_base, exts, allowed_filenames)
        except GithubException as e:
            if e.status == 403:
                logger.warning("Límite de tasa excedido al descargar %s para %s. Se omitirá esta ruta.", github_path, package)
            else:
                logger.error("Error al descargar %s para %s: %s", github_path, package, e)

def main():
    for package_name, config in packages_config.items():
        logger.info("=== Descargando archivos para el paquete: %s ===", package_name)
        download_package(package_name, config)
    logger.info("Descarga completada.")

if __name__ == "__main__":
    main()
