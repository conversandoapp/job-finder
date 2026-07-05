# Imagen para desplegar el backend (que además sirve el frontend estático)
# en Cloud Run. Se construye desde la raíz de job-finder/ (este mismo
# directorio), así que el contexto de build incluye tanto backend/ como
# frontend/.

FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias primero (cachea mejor entre builds)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copiar el resto del proyecto
COPY backend backend
COPY frontend frontend

WORKDIR /app/backend

# Cloud Run inyecta la variable PORT en runtime (normalmente 8080).
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
