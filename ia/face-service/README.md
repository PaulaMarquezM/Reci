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

## Probar una webcam USB

Una webcam USB se conecta a la Mac (o a la futura Raspberry Pi), no al ESP32.
Primero comprueba que se vea en QuickTime o Photo Booth. Luego, con la web y
este servicio ya ejecutándose, usa el probador integrado:

```bash
cd ia/face-service
source .venv/bin/activate
python scripts/probar_webcam.py
```

Se abre una vista previa. Presiona **Espacio** para enviar el fotograma actual
a `/api/face/recognize`; presiona **Q** para salir. El script no guarda fotos.

Si abre la cámara interna en vez de la webcam USB, ciérralo y prueba:

```bash
python scripts/probar_webcam.py --camera 1
```

En macOS permite que Terminal acceda a **Cámara** en Ajustes del Sistema →
Privacidad y seguridad → Cámara. El script lee `ROBOT_API_KEY` desde
`web/.env.local` sin imprimirla.

## Contenedor

```bash
docker build -t reci-face-service .
docker run --rm -p 8000:8000 -e FACE_SERVICE_API_KEY='cambia-esto' reci-face-service
```

No publiques este servicio en Internet sin una capa de red privada o un proxy
que limite su acceso al backend de Reci.
