FROM python:3.9-slim

WORKDIR /app

# Copia todos los archivos de la carpeta app al contenedor
COPY . /app

# Instala las dependencias definidas en requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 8000, pero recuerda que cada servicio define su propio comando para iniciar.
EXPOSE 8000

# CMD por defecto; este comando se sobrescribe en docker-compose mediante la directiva command.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
