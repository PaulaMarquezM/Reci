FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Solo dependencias de runtime. Las de entrenamiento y pruebas viven en
# requirements-dev.txt y no entran aquí: el servicio nunca entrena, solo
# ejecuta model.tflite con ai-edge-litert.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY expert_system/ ./expert_system/
COPY vision/ ./vision/
COPY model/ ./model/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
