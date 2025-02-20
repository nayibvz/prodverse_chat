# Usa una imagen base ligera de Python
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia todo el contenido de la aplicación al contenedor
COPY . /app

# Instala las dependencias definidas en requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Exponer puertos que se utilizarán. Aquí se expone el puerto 8000, pero cada servicio puede mapearlo a otro.
EXPOSE 8000

# CMD por defecto (este se sobrescribe en docker-compose con la directiva command)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
