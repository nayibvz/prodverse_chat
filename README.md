API RAG de Grafos

Trabajo Final de Máster

Universidad Complutense de Madrid

## Descripción del Proyecto
El presente proyecto tiene como objetivo desarrollar un pipeline integral para la preparación y disponibilización de datos extraídos de diversas fuentes documentales asociadas a paquetes de R open source, en concreto faucet y taplock, desarrollados por la organización ixpantia. La solución se fundamenta en la aplicación de técnicas de generación aumentada por recuperación (RAG), que optimizan la salida de los modelos de lenguaje de gran tamaño al incorporar información relevante de bases de conocimiento externas antes de generar una respuesta.

El sistema permite extraer automáticamente la documentación y ejemplos de código desde repositorios de GitHub, procesar estos archivos en fragmentos (chunks) conservando su contexto semántico, generar embeddings mediante la API de OpenAI y almacenar toda la información en una base de datos de grafos (Neo4j). Además, se expone una API desarrollada en FastAPI y se implementa una interfaz de usuario en Streamlit, que simula una experiencia de chat similar a ChatGPT para interactuar de manera intuitiva con la documentación.

## Características
Extracción Automática: Descarga de documentación y ejemplos de código desde GitHub.
Procesamiento y Chunking: División del contenido en fragmentos utilizando técnicas adaptadas a texto y código, preservando el contexto semántico.
Generación de Embeddings: Uso de la API de OpenAI para generar representaciones numéricas del contenido.
Almacenamiento en Grafos: Indexación de los chunks en Neo4j junto con metadatos (ruta, carpeta, paquete) y creación de relaciones para enriquecer el contexto.
API de Consulta: Desarrollo de una API en FastAPI que permite realizar búsquedas semánticas y responder preguntas utilizando el enfoque RAG.
Interfaz de Usuario: Implementación de una interfaz en Streamlit que permite a los usuarios interactuar mediante un chat.
Pipeline Automatizado: Integración de scripts ETL orquestados mediante Docker y Docker Compose para actualizar y gestionar la información.

## Instalación y Ejecución

## 1. Variables de Entorno
Crea un archivo .env en la raíz del proyecto (no lo subas a GitHub) con el siguiente contenido:

```
OPENAI_API_KEY=sk-...  # Tu API Key de OpenAI
NEO4J_PASSWORD=testing1
NEO4J_URI=bolt://neo4j:7687  # O "bolt://localhost:7687" si se ejecuta localmente
GITHUB_TOKEN=github_pat_...
```

## 2. Construcción y Ejecución con Docker Compose
El proyecto se orquesta mediante Docker Compose. Para construir y levantar todos los contenedores, ejecuta:

```
docker-compose up --build
Esto levantará los siguientes servicios:
```

### Neo4j: Base de datos de grafos.
### API: Servicio que expone la API desarrollada con FastAPI.
### Streamlit App: Interfaz de usuario tipo chat para interactuar con la API.
### ETL Pipeline (run_all): Script que descarga la documentación, realiza el chunking y almacena los datos en Neo4j.

## 3. Acceso a la Aplicación
Interfaz de Usuario (Streamlit):
Accede a través de la URL asignada, por ejemplo:
http://localhost:8501

### API (FastAPI):
La documentación de la API se encuentra en:
http://localhost:8000/docs

### Uso de la Herramienta
Interacción con el Chat
La interfaz en Streamlit ofrece una experiencia de chat. El usuario debe:

Seleccionar el paquete de interés (por ejemplo, faucet o taplock).
Escribir la pregunta en el campo de entrada.
Recibir la respuesta generada por el sistema, que utiliza el enfoque RAG para combinar información recuperada de la documentación con la capacidad de generación de texto de OpenAI.
Consultas a la API

La API permite realizar:
Búsquedas de chunks: Recupera nodos de tipo Chunk mediante filtros.
Búsquedas semánticas: Utiliza la similitud de coseno entre embeddings para ordenar los resultados.
Respuestas mediante chat (RAG): Filtra las consultas fuera de dominio y genera respuestas detalladas.
