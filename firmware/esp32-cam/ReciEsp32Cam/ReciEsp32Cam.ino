// Reci · ESP32-CAM compatible AI Thinker (OV2640 u OV3660) · clasificación
// de residuos + saludo facial
//
// El Monitor Serial envía C para iniciar una lectura: la cámara toma tres
// fotos con iluminación externa. Cada foto aporta un voto del proveedor y
// otro del modelo local; el Mega abre una compuerta solo si existe una mayoría
// simple priorizando la mayoría del proveedor y usando el modelo local como
// respaldo. El resultado final (ya votado) se registra una sola vez en
// recycle_events; si nadie fue
// identificado, el Mega muestra en el OLED el QR para reclamar los puntos
// desde la app — ver docs/DECISION-QR-RECLAMO.md.
//
// Cuando el PIR del Mega detecta presencia, manda "RECI:PRESENCE:detected"
// por el mismo UART. La ESP32-CAM toma una foto y la manda a
// /api/face/recognize (opt-in, ver docs/DECISION-SERVICIO-FACIAL.md); si hay
// coincidencia pide el saludo personalizado a /api/robot/display y lo
// muestra en la LCD del Mega.

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include "esp_camera.h"

#include "ReciEsp32CamSecrets.h"

namespace {

constexpr int kCameraPwdn = 32;
constexpr int kCameraReset = -1;
constexpr int kCameraXclk = 0;
constexpr int kCameraSiod = 26;
constexpr int kCameraSioc = 27;
constexpr int kCameraY9 = 35;
constexpr int kCameraY8 = 34;
constexpr int kCameraY7 = 39;
constexpr int kCameraY6 = 36;
constexpr int kCameraY5 = 21;
constexpr int kCameraY4 = 19;
constexpr int kCameraY3 = 18;
constexpr int kCameraY2 = 5;
constexpr int kCameraVsync = 25;
constexpr int kCameraHref = 23;
constexpr int kCameraPclk = 22;
constexpr int kFlashLedPin = 4;
// El LED integrado produce picos de corriente que reinician algunas ESP32-CAM
// alimentadas por USB. Para esta prueba usa una luz externa frontal.
constexpr bool kUseFlashLed = false;
constexpr int kMegaRxPin = 13;
constexpr int kMegaTxPin = 14;
constexpr unsigned long kMegaBaud = 9600;
constexpr unsigned long kFlashWarmupMs = 220UL;
constexpr unsigned long kCaptureIntervalMs = 350UL;
// PUCEM_INVITADOS puede tardar más de 20 s en asignar la conexión a la placa.
// CameraWebServer validó que esta misma red sí conecta si se le da más tiempo.
constexpr unsigned long kWiFiConnectTimeoutMs = 60'000UL;
// El backend puede esperar hasta 25 s al proveedor de visión. El valor por
// defecto de HTTPClient (5 s) producía el error -11 aunque la foto sí se
// hubiera enviado; dejamos un pequeño margen para la respuesta local.
constexpr uint16_t kVisionHttpTimeoutMs = 30'000;
constexpr uint8_t kCaptureCount = 3;
constexpr char kBoundary[] = "ReciMaterialBoundary2026";



HardwareSerial mega(1);

struct MaterialVotes {
  uint8_t plastico = 0;
  uint8_t vidrio = 0;
  uint8_t abstenciones = 0;
  float plasticoConfidence = 0;
  float vidrioConfidence = 0;
};

class MultipartCameraStream final : public Stream {
 public:
  MultipartCameraStream(const String& prefix, const uint8_t* image, size_t imageLength, const String& suffix)
      : _prefix(prefix), _image(image), _imageLength(imageLength), _suffix(suffix) {}

  size_t totalLength() const { return _prefix.length() + _imageLength + _suffix.length(); }
  int available() override { return static_cast<int>(totalLength() - _position); }
  int peek() override { return -1; }
  void flush() override {}
  size_t write(uint8_t) override { return 0; }

  int read() override {
    if (_position >= totalLength()) return -1;
    const size_t prefixLength = _prefix.length();
    const size_t imageEnd = prefixLength + _imageLength;
    const int value = _position < prefixLength
        ? static_cast<uint8_t>(_prefix[_position])
        : _position < imageEnd
          ? _image[_position - prefixLength]
          : static_cast<uint8_t>(_suffix[_position - imageEnd]);
    ++_position;
    return value;
  }

 private:
  const String& _prefix;
  const uint8_t* _image;
  size_t _imageLength;
  const String& _suffix;
  size_t _position = 0;
};

void sendMega(const String& command) {
  mega.println(command);
  Serial.print(F("MEGA <- "));
  Serial.println(command);
}

void showOnLcd(const String& firstLine, const String& secondLine) {
  sendMega("CMD:LCD:" + firstLine + "|" + secondLine);
}

bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  // En redes de campus la ESP32-CAM puede perder la asociación durante el
  // ahorro de energía. La configuración coincide con CameraWebServer, que
  // ya se validó con esta misma placa y red.
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print(F("Conectando al Wi-Fi"));
  const unsigned long deadline = millis() + kWiFiConnectTimeoutMs;
  while (WiFi.status() != WL_CONNECTED && static_cast<long>(millis() - deadline) < 0) {
    delay(300);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("ERROR: no se pudo conectar al Wi-Fi"));
    showOnLcd("Error de WiFi", "Revisa Reci");
    return false;
  }
  Serial.print(F("Wi-Fi listo: "));
  Serial.println(WiFi.localIP());
  return true;
}

bool startCamera() {
  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = kCameraY2;
  config.pin_d1 = kCameraY3;
  config.pin_d2 = kCameraY4;
  config.pin_d3 = kCameraY5;
  config.pin_d4 = kCameraY6;
  config.pin_d5 = kCameraY7;
  config.pin_d6 = kCameraY8;
  config.pin_d7 = kCameraY9;
  config.pin_xclk = kCameraXclk;
  config.pin_pclk = kCameraPclk;
  config.pin_vsync = kCameraVsync;
  config.pin_href = kCameraHref;
  config.pin_sccb_sda = kCameraSiod;
  config.pin_sccb_scl = kCameraSioc;
  config.pin_pwdn = kCameraPwdn;
  config.pin_reset = kCameraReset;
  config.xclk_freq_hz = 20'000'000;
  config.pixel_format = PIXFORMAT_JPEG;
  // QVGA (320x240) es suficiente para la clasificación de plástico/vidrio,
  // acelera la transferencia al backend y deja más memoria libre.
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println(F("ERROR: no se pudo iniciar la cámara"));
    showOnLcd("Error de camara", "Revisa Reci");
    return false;
  }
  // El driver detecta el sensor conectado. En la placa OV3660 actual debe
  // verse PID 0x3660; si aparece otro PID, la cámara puede funcionar igual,
  // pero se debe registrar el hardware real de la prueba.
  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    Serial.printf("Sensor de camara detectado: PID=0x%04X\n", sensor->id.PID);
  }
  Serial.println(F("Camara en QVGA (optimizada)"));
  return true;
}

camera_fb_t* captureIlluminatedFrame() {
  if (kUseFlashLed) {
    digitalWrite(kFlashLedPin, HIGH);
    delay(kFlashWarmupMs);
  }
  camera_fb_t* frame = esp_camera_fb_get();
  if (kUseFlashLed) digitalWrite(kFlashLedPin, LOW);
  return frame;
}

String postClassify(camera_fb_t* frame, int& statusCode) {
  WiFiClient client;
  HTTPClient http;
  const String url = String(RECI_API_BASE_URL) + "/api/vision/classify";
  String prefix = String("--") + kBoundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"record_event\"\r\n\r\nfalse\r\n--";
  prefix += kBoundary;
  prefix += "\r\nContent-Disposition: form-data; name=\"image\"; filename=\"residuo.jpg\"\r\n";
  prefix += "Content-Type: image/jpeg\r\n\r\n";
  const String suffix = String("\r\n--") + kBoundary + "--\r\n";
  MultipartCameraStream payload(prefix, frame->buf, frame->len, suffix);

  if (!http.begin(client, url)) {
    statusCode = -1;
    return "";
  }
  http.setTimeout(kVisionHttpTimeoutMs);
  http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
  http.addHeader("Content-Type", String("multipart/form-data; boundary=") + kBoundary);
  statusCode = http.sendRequest("POST", &payload, payload.totalLength());
  const String body = statusCode > 0 ? http.getString() : "";
  http.end();
  return body;
}

void addVote(MaterialVotes& votes, const String& material, float confidence) {
  if (material == "plastico") {
    ++votes.plastico;
    votes.plasticoConfidence += confidence;
  } else if (material == "vidrio") {
    ++votes.vidrio;
    votes.vidrioConfidence += confidence;
  } else {
    ++votes.abstenciones;
  }
}

String majorityMaterial(const MaterialVotes& votes) {
  const uint8_t totalValidVotes = votes.plastico + votes.vidrio;
  // Una sola predicción nunca abre una compuerta. Desconocido es una
  // abstención, así que no cuenta dentro de este mínimo ni rompe empates.
  if (totalValidVotes < 2) return "desconocido";
  if (votes.plastico > votes.vidrio) return "plastico";
  if (votes.vidrio > votes.plastico) return "vidrio";
  return "desconocido";
}

String chooseMaterial(const MaterialVotes& providerVotes,
                      const MaterialVotes& localVotes,
                      bool& usedProvider) {
  const String providerMaterial = majorityMaterial(providerVotes);
  if (providerMaterial != "desconocido") {
    usedProvider = true;
    return providerMaterial;
  }

  const String localMaterial = majorityMaterial(localVotes);
  if (localMaterial != "desconocido") {
    usedProvider = false;
    return localMaterial;
  }

  usedProvider = false;
  return "desconocido";
}

// Registra el resultado final (ya votado) en recycle_events — las 3 fotos
// individuales de arriba usan record_event=false a propósito, para no
// crear tres filas por un solo depósito. Como nadie está identificado
// todavía en este flujo (sin reconocimiento facial aquí), el backend genera
// un claim_code de un solo uso para el QR de puntos — ver
// docs/DECISION-QR-RECLAMO.md. Devuelve "" si no hay claim_code (falló el
// registro, o el material vino "desconocido" y no aplica).
String recordRecycleEvent(const String& material, float confidence) {
  WiFiClient client;
  HTTPClient http;
  const String url = String(RECI_API_BASE_URL) + "/api/events/recycle";
  if (!http.begin(client, url)) return "";

  JsonDocument body;
  body["material"] = material;
  body["confidence"] = confidence;
  String payload;
  serializeJson(body, payload);

  http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
  http.addHeader("Content-Type", "application/json");
  const int statusCode = http.POST(payload);
  const String responseBody = statusCode > 0 ? http.getString() : "";
  http.end();

  if (statusCode != HTTP_CODE_CREATED) {
    Serial.printf("ERROR: /events/recycle respondio %d\n", statusCode);
    return "";
  }

  JsonDocument document;
  if (deserializeJson(document, responseBody)) return "";
  return document["event"]["claim_code"] | "";
}

String postFaceRecognize(camera_fb_t* frame, int& statusCode) {
  WiFiClient client;
  HTTPClient http;
  const String url = String(RECI_API_BASE_URL) + "/api/face/recognize";
  String prefix = String("--") + kBoundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"image\"; filename=\"visitante.jpg\"\r\n";
  prefix += "Content-Type: image/jpeg\r\n\r\n";
  const String suffix = String("\r\n--") + kBoundary + "--\r\n";
  MultipartCameraStream payload(prefix, frame->buf, frame->len, suffix);

  if (!http.begin(client, url)) {
    statusCode = -1;
    return "";
  }
  http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
  http.addHeader("Content-Type", String("multipart/form-data; boundary=") + kBoundary);
  statusCode = http.sendRequest("POST", &payload, payload.totalLength());
  const String body = statusCode > 0 ? http.getString() : "";
  http.end();
  return body;
}

// Trae las dos líneas de saludo ya armadas por el backend para no duplicar
// aquí el "Bienvenido, <nombre>" — ver GET /api/robot/display en
// docs/API-ROBOT.md.
bool fetchGreetingLines(const String& profileId, String& firstLine, String& secondLine) {
  WiFiClient client;
  HTTPClient http;
  const String url = String(RECI_API_BASE_URL) + "/api/robot/display?profile_id=" + profileId;
  if (!http.begin(client, url)) return false;
  http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
  const int statusCode = http.GET();
  const String body = statusCode == HTTP_CODE_OK ? http.getString() : "";
  http.end();
  if (statusCode != HTTP_CODE_OK) return false;

  JsonDocument document;
  if (deserializeJson(document, body)) return false;
  firstLine = document["lines"][0] | "";
  secondLine = document["lines"][1] | "";
  return firstLine.length() > 0;
}

void greetVisitor() {
  if (WiFi.status() != WL_CONNECTED && !connectWiFi()) return;

  Serial.println(F("--- PRESENCIA DETECTADA: reconocimiento facial ---"));
  camera_fb_t* frame = captureIlluminatedFrame();
  if (frame == nullptr) {
    Serial.println(F("ERROR: no se pudo capturar foto para reconocimiento facial"));
    return;
  }

  int statusCode = 0;
  const String body = postFaceRecognize(frame, statusCode);
  esp_camera_fb_return(frame);

  if (statusCode != HTTP_CODE_OK) {
    Serial.printf("ERROR: /face/recognize respondio %d\n", statusCode);
    return;
  }

  JsonDocument document;
  if (deserializeJson(document, body)) {
    Serial.println(F("ERROR: JSON invalido en /face/recognize"));
    return;
  }

  if (!(document["matched"] | false)) {
    Serial.println(F("Reconocimiento facial: sin coincidencia"));
    showOnLcd("Hola, soy Reci", "Recicla y gana");
    return;
  }

  const String profileId = document["profile_id"].as<String>();
  const String displayName = document["display_name"].as<String>();
  Serial.print(F("Reconocimiento facial: "));
  Serial.println(displayName);

  String firstLine;
  String secondLine;
  if (fetchGreetingLines(profileId, firstLine, secondLine)) {
    showOnLcd(firstLine, secondLine);
  } else {
    showOnLcd("Bienvenido,", displayName);
  }
}

void classifyResidue() {
  if (WiFi.status() != WL_CONNECTED && !connectWiFi()) return;

  Serial.println(F("--- CLASIFICANDO RESIDUO: 3 fotos ---"));
  sendMega("CMD:FACE:thinking");
  showOnLcd("Analizando residuo", "No lo retires");
  MaterialVotes votes;
  MaterialVotes providerVotes;
  MaterialVotes localVotes;

  for (uint8_t index = 0; index < kCaptureCount; ++index) {
    camera_fb_t* frame = captureIlluminatedFrame();
    if (frame == nullptr) {
      Serial.printf("ERROR: no se pudo capturar foto %u\n", index + 1);
      continue;
    }
    int statusCode = 0;
    const String body = postClassify(frame, statusCode);
    esp_camera_fb_return(frame);
    if (statusCode != HTTP_CODE_OK) {
      Serial.printf("ERROR: foto %u /vision/classify respondio %d\n", index + 1, statusCode);
      continue;
    }
    JsonDocument document;
    if (deserializeJson(document, body)) {
      Serial.printf("ERROR: JSON invalido en foto %u\n", index + 1);
      continue;
    }
    // Cada respuesta trae los votos independientes de la misma foto. No se
    // fusionan aquí: tras tres fotos, el firmware decide con hasta seis votos.
    JsonArrayConst photoVotes = document["vision_votes"].as<JsonArrayConst>();
    uint8_t receivedVotes = 0;
    String providerMaterial = "no_disponible";
    float providerConfidence = 0.0F;
    String localMaterial = "no_disponible";
    float localConfidence = 0.0F;
    for (JsonVariantConst vote : photoVotes) {
      const String source = vote["source"].as<String>();
      const String voteMaterial = vote["material"].as<String>();
      const float voteConfidence = vote["confidence"] | 0.0F;
      addVote(votes, voteMaterial, voteConfidence);
      if (source == "openai_sistema_experto") {
        addVote(providerVotes, voteMaterial, voteConfidence);
      } else if (source == "modelo_local") {
        addVote(localVotes, voteMaterial, voteConfidence);
      }
      ++receivedVotes;

      if (source == "openai_sistema_experto") {
        providerMaterial = voteMaterial;
        providerConfidence = voteConfidence;
      } else if (source == "modelo_local") {
        localMaterial = voteMaterial;
        localConfidence = voteConfidence;
      }
    }

    // El modelo de comparación es opcional y no se suma a los votos. Permite
    // contrastar los dos TFLite sobre la misma foto de la ESP32-CAM sin que
    // afecte la apertura de compuertas.
    String shadowMaterial = "no_configurado";
    float shadowConfidence = 0.0F;
    JsonVariantConst shadowResult = document["vision_local_shadow_result"];
    if (!shadowResult.isNull()) {
      shadowMaterial = shadowResult["material"] | "no_disponible";
      shadowConfidence = shadowResult["confidence"] | 0.0F;
    }

    // Compatibilidad con un servicio de visión anterior durante un despliegue
    // gradual: si no envía vision_votes, conserva su único resultado.
    if (receivedVotes == 0) {
      const String material = document["material"].as<String>();
      const float confidence = document["confidence"] | 0.0F;
      addVote(votes, material, confidence);
      addVote(providerVotes, material, confidence);
      Serial.printf("foto %u: respaldo=%s (%.2f)\n", index + 1, material.c_str(), confidence);
    } else {
      Serial.printf(
          "foto %u: OpenAI=%s (%.2f) | modelo=%s (%.2f)\n",
          index + 1,
          providerMaterial.c_str(),
          providerConfidence,
          localMaterial.c_str(),
          localConfidence);
      if (shadowMaterial != "no_configurado") {
        Serial.printf(
            "foto %u: comparacion local activo=%s (%.2f) | sombra=%s (%.2f) [sin voto]\n",
            index + 1,
            localMaterial.c_str(),
            localConfidence,
            shadowMaterial.c_str(),
            shadowConfidence);
      }
    }
    if (index + 1 < kCaptureCount) delay(kCaptureIntervalMs);
  }

  Serial.printf(
      "Votos validos: plastico=%u | vidrio=%u | abstenciones=%u\n",
      votes.plastico,
      votes.vidrio,
      votes.abstenciones);
  Serial.printf(
      "Votos OpenAI: plastico=%u | vidrio=%u | abstenciones=%u\n",
      providerVotes.plastico,
      providerVotes.vidrio,
      providerVotes.abstenciones);
  Serial.printf(
      "Votos modelo: plastico=%u | vidrio=%u | abstenciones=%u\n",
      localVotes.plastico,
      localVotes.vidrio,
      localVotes.abstenciones);

  bool usedProvider = false;
  const String material = chooseMaterial(providerVotes, localVotes, usedProvider);
  if (material == "desconocido") {
    Serial.println(F("Resultado: DESCONOCIDO (sin mayoria segura)"));
    sendMega("CMD:FACE:confused");
    showOnLcd("No estoy seguro", "Intenta de nuevo");
    return;
  }

  Serial.print(F("Resultado final: "));
  Serial.println(material);

  Serial.print(F("Regla de decision: "));
  Serial.println(usedProvider ? F("mayoria OpenAI/sistema experto")
                              : F("respaldo por mayoria del modelo local"));

  const MaterialVotes& winningVotes = usedProvider ? providerVotes : localVotes;
  const float winningConfidence = material == "plastico"
      ? (winningVotes.plastico > 0
          ? winningVotes.plasticoConfidence / winningVotes.plastico
          : 0.0F)
      : (winningVotes.vidrio > 0
          ? winningVotes.vidrioConfidence / winningVotes.vidrio
          : 0.0F);
  const String claimCode = recordRecycleEvent(material, winningConfidence);

  sendMega("CMD:CLASSIFY:" + material);
  sendMega("CMD:FACE:happy");

  if (claimCode.length() > 0) {
    sendMega("CMD:QR:" + claimCode);
    showOnLcd(material == "vidrio" ? "VIDRIO" : "PLASTICO", "Escanea el QR");
  } else {
    showOnLcd(material == "vidrio" ? "VIDRIO" : "PLASTICO", "Compuerta abierta");
  }
}

void readClassificationRequest() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(Serial.read());
    if (command == 'c' || command == 'C') classifyResidue();
    // 'F' dispara el mismo reconocimiento facial que el PIR, para probarlo
    // sin depender de que el sensor de presencia ya esté cableado.
    if (command == 'f' || command == 'F') greetVisitor();
  }
}

void readMegaEvents() {
  static String line;
  while (mega.available() > 0) {
    const char character = static_cast<char>(mega.read());
    if (character == '\r') continue;
    if (character == '\n') {
      if (line == "RECI:PRESENCE:detected") greetVisitor();
      line = "";
      continue;
    }
    line += character;
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  mega.begin(kMegaBaud, SERIAL_8N1, kMegaRxPin, kMegaTxPin);
  pinMode(kFlashLedPin, OUTPUT);
  digitalWrite(kFlashLedPin, LOW);
  delay(500);

  showOnLcd("Hola, soy Reci", "Preparando camara");
  if (!startCamera()) return;
  if (!connectWiFi()) return;
  showOnLcd("Hola, soy Reci", "Envia C para leer");
  sendMega("CMD:FACE:idle");
  Serial.println(F("Listo. Envia C para clasificar un residuo, F para probar el reconocimiento facial."));
}

void loop() {
  readClassificationRequest();
  readMegaEvents();
}
