FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY services/vision/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# El build context es la raíz del monorepo. El servicio solo conserva su
# adaptador HTTP; reglas, heurísticas y prompt vienen del núcleo compartido.
COPY services/vision/main.py services/vision/cloud_classifier.py ./services/vision/
COPY expert_system/ ./expert_system/
COPY vision/attribute_extractor.py vision/visual_heuristics.py vision/vision_config.py vision/clasificacion_log.py ./vision/

EXPOSE 8000
CMD ["uvicorn", "services.vision.main:app", "--host", "0.0.0.0", "--port", "8000"]
