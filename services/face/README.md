# Servicio facial de Reci

Servicio FastAPI privado que extrae embeddings de una imagen con DeepFace y
Facenet512. No persiste fotos ni vectores: el backend Next.js cifra los vectores
antes de escribirlos en Supabase.

## Variables necesarias

```bash
FACE_SERVICE_API_KEY=<secreto-compartido-con-la-web>
FACE_MODEL_NAME=Facenet512
FACE_DETECTOR_BACKEND=opencv
```

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FACE_SERVICE_API_KEY='cambia-esto'
uvicorn main:app --reload --port 8000
```

También puedes guardar esas variables en un archivo `.env` dentro de esta misma
carpeta; el servicio lo carga automáticamente al iniciar.

El backend web debe tener el mismo secreto en `FACE_SERVICE_API_KEY` y apuntar
`FACE_SERVICE_URL=http://localhost:8000` durante desarrollo.

## Contenedor

```bash
docker build -t reci-face-service .
docker run --rm -p 8000:8000 -e FACE_SERVICE_API_KEY='cambia-esto' reci-face-service
```

No publiques este servicio en Internet sin una capa de red privada o un proxy
que limite su acceso al backend de Reci.
