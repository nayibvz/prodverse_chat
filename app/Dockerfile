# Usa una imagen base de Python ligera
FROM python:3.9-slim

# Establece el directorio de trabajo a /app
WORKDIR /app

# Copia todos los archivos del directorio local 'app' al contenedor en /app
COPY . /app

# Instala las dependencias desde requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Expone el puerto 8000, que se usará para la API
EXPOSE 8000

# Comando para ejecutar la API usando Uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
