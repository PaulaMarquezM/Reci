// Reci · ESP32-CAM AI Thinker · clasificación de residuos
//
// El Monitor Serial envía C para iniciar una lectura: la cámara toma tres
// fotos con iluminación externa, el backend clasifica cada una y el Mega abre una compuerta
// solo si existe una mayoría segura de plástico o vidrio. El resultado final
// (ya votado) se registra una sola vez en recycle_events; si nadie fue
// identificado, el Mega muestra en el OLED el QR para reclamar los puntos
// desde la app — ver docs/DECISION-QR-RECLAMO.md.

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include "esp_camera.h"
#include <time.h>

#include "ReciEsp32CamSecrets.h"
#include "ReciHttpClient.h"
#include "RobotCallDispatcher.h"

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
constexpr unsigned long kWiFiConnectTimeoutMs = 60'000UL;
constexpr unsigned long kClockSyncTimeoutMs = 15000UL;
constexpr uint16_t kVisionHttpTimeoutMs = 30'000;
constexpr uint8_t kCaptureCount = 3;
constexpr char kBoundary[] = "ReciMaterialBoundary2026";

HardwareSerial mega(1);
ReciRobotCallDispatcher dispatcher(mega);
bool lastRecycleLinkedToCall = false;

struct MaterialVotes {
  uint8_t plastico = 0;
  uint8_t vidrio = 0;
  uint8_t abstenciones = 0;
  float plasticoConfidence = 0;
  float vidrioConfidence = 0;
};

struct FinalDecision {
  String material = "desconocido";
  String source = "respuesta_incompleta";
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

  if (String(RECI_API_BASE_URL).startsWith("https://")) {
    configTime(0, 0, "pool.ntp.org", "time.google.com");
    const unsigned long clockDeadline = millis() + kClockSyncTimeoutMs;
    while (time(nullptr) < 1'700'000'000L &&
           static_cast<long>(millis() - clockDeadline) < 0) {
      delay(200);
    }
    if (time(nullptr) < 1'700'000'000L) {
      Serial.println(F("ERROR: no se pudo sincronizar el reloj para HTTPS"));
      showOnLcd("Error de reloj", "Revisa Internet");
      return false;
    }
    Serial.println(F("HTTPS: reloj y certificado listos."));
  }
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
  // QVGA mantiene el dominio con el que se validó el modelo y evita agotar
  // memoria durante las tres capturas de la OV3660.
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println(F("ERROR: no se pudo iniciar la cámara"));
    showOnLcd("Error de camara", "Revisa Reci");
    return false;
  }
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
  const String url = String(RECI_API_BASE_URL) + "/api/vision/classify";
  ReciHttpClient client(url);
  HTTPClient http;
  String prefix = String("--") + kBoundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"record_event\"\r\n\r\nfalse\r\n--";
  prefix += kBoundary;
  prefix += "\r\nContent-Disposition: form-data; name=\"image\"; filename=\"residuo.jpg\"\r\n";
  prefix += "Content-Type: image/jpeg\r\n\r\n";
  const String suffix = String("\r\n--") + kBoundary + "--\r\n";
  MultipartCameraStream payload(prefix, frame->buf, frame->len, suffix);

  if (!http.begin(client.get(), url)) {
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
  if (votes.plastico < 2 && votes.vidrio < 2) return "desconocido";
  if (votes.plastico == votes.vidrio) return "desconocido";
  return votes.plastico > votes.vidrio ? "plastico" : "vidrio";
}

FinalDecision decideMaterial(const MaterialVotes& providerVotes,
                             const MaterialVotes& localVotes,
                             bool capturesComplete) {
  if (!capturesComplete) return {"desconocido", "respuesta_incompleta"};

  const String providerMaterial = majorityMaterial(providerVotes);
  if (providerMaterial != "desconocido") {
    return {providerMaterial, "openai_sistema_experto"};
  }

  const uint8_t providerValidVotes = providerVotes.plastico + providerVotes.vidrio;
  if (providerValidVotes == 0) {
    return {"desconocido", "tres_abstenciones_proveedor"};
  }
  if (providerValidVotes != 1) {
    return {"desconocido", "proveedor_contradictorio"};
  }

  const String providerSingleVote = providerVotes.plastico == 1 ? "plastico" : "vidrio";
  const String localMaterial = majorityMaterial(localVotes);
  if (localMaterial == providerSingleVote) {
    return {localMaterial, "modelo_local_respaldo"};
  }
  if (localMaterial != "desconocido") {
    return {"desconocido", "fuentes_contradictorias"};
  }
  return {"desconocido", "sin_mayoria"};
}

// Registra el resultado final (ya votado) en recycle_events — las 3 fotos
// individuales de arriba usan record_event=false a propósito, para no
// crear tres filas por un solo depósito. Si RECI acaba de atender una
// llamada, se adjuntan call_id y robot_point_id para acreditar directamente
// a esa persona. Sin una llamada reciente, el backend genera un claim_code
// de un solo uso para el QR de puntos — ver docs/DECISION-QR-RECLAMO.md.
String recordRecycleEvent(const String& material, float confidence) {
  lastRecycleLinkedToCall = false;
  const String url = String(RECI_API_BASE_URL) + "/api/events/recycle";
  ReciHttpClient client(url);
  HTTPClient http;
  if (!http.begin(client.get(), url)) return "";

  JsonDocument body;
  body["material"] = material;
  body["confidence"] = confidence;
  const bool linkedToCall = dispatcher.addRecycleContext(body);
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

  // El contexto se consume una sola vez. Un segundo depósito necesitará
  // otra llamada o se entregará mediante un nuevo QR.
  if (linkedToCall) {
    lastRecycleLinkedToCall = true;
    dispatcher.clearRecycleContext();
  }

  JsonDocument document;
  if (deserializeJson(document, responseBody)) return "";
  return document["event"]["claim_code"] | "";
}

void classifyResidue() {
  if (WiFi.status() != WL_CONNECTED && !connectWiFi()) return;

  Serial.println(F("--- CLASIFICANDO RESIDUO: 3 fotos ---"));
  sendMega("CMD:FACE:thinking");
  showOnLcd("Analizando residuo", "No lo retires");
  MaterialVotes providerVotes;
  MaterialVotes localVotes;
  bool capturesComplete = true;

  for (uint8_t index = 0; index < kCaptureCount; ++index) {
    camera_fb_t* frame = captureIlluminatedFrame();
    if (frame == nullptr) {
      Serial.printf("ERROR: no se pudo capturar foto %u\n", index + 1);
      capturesComplete = false;
      continue;
    }
    int statusCode = 0;
    const String body = postClassify(frame, statusCode);
    esp_camera_fb_return(frame);
    if (statusCode != HTTP_CODE_OK) {
      Serial.printf("ERROR: foto %u /vision/classify respondio %d\n", index + 1, statusCode);
      capturesComplete = false;
      continue;
    }
    JsonDocument document;
    if (deserializeJson(document, body)) {
      Serial.printf("ERROR: JSON invalido en foto %u\n", index + 1);
      capturesComplete = false;
      continue;
    }

    // Cada foto debe traer exactamente un diagnóstico del proveedor y uno
    // del modelo local. Si falta uno, llega mal formado o viene de un
    // servicio heredado sin vision_votes, se conserva como evidencia pero no
    // se permite abrir ninguna compuerta.
    JsonArrayConst photoVotes = document["vision_votes"].as<JsonArrayConst>();
    bool providerReceived = false;
    bool localReceived = false;
    bool responseComplete = !photoVotes.isNull();
    String providerMaterial = "no_disponible";
    float providerConfidence = 0.0F;
    String localMaterial = "no_disponible";
    float localConfidence = 0.0F;

    if (responseComplete) {
      for (JsonVariantConst vote : photoVotes) {
        const String source = vote["source"] | "";
        const String material = vote["material"] | "";
        const float confidence = vote["confidence"] | 0.0F;
        const bool countsAsVote = vote["counts_as_vote"] | false;
        const bool providerVote = source == "openai_sistema_experto";
        const bool localVote = source == "modelo_local";
        const bool knownMaterial = material == "plastico" || material == "vidrio";

        if ((!providerVote && !localVote) || (!knownMaterial && material != "desconocido")) {
          responseComplete = false;
          continue;
        }
        if (providerVote) {
          if (providerReceived || countsAsVote != knownMaterial) {
            responseComplete = false;
            continue;
          }
          providerReceived = true;
          providerMaterial = material;
          providerConfidence = confidence;
          addVote(providerVotes, material, confidence);
        } else {
          // MobileNetV3-Large es binario: una abstención local equivale a
          // respuesta incompleta, no a permiso para usar su mayoría.
          if (localReceived || !knownMaterial || !countsAsVote) {
            responseComplete = false;
            continue;
          }
          localReceived = true;
          localMaterial = material;
          localConfidence = confidence;
          addVote(localVotes, material, confidence);
        }
      }
    }

    if (!providerReceived || !localReceived) responseComplete = false;
    if (!responseComplete) {
      capturesComplete = false;
      if (photoVotes.isNull()) {
        Serial.printf("ERROR: foto %u sin vision_votes (rechazo seguro)\n", index + 1);
      } else {
        Serial.printf("ERROR: foto %u con vision_votes incompletos\n", index + 1);
      }
    }

    // El modelo de comparación es opcional y solo se registra; nunca entra
    // en providerVotes/localVotes ni modifica la decisión.
    JsonVariantConst shadowResult = document["vision_local_shadow_result"];
    const String shadowMaterial = shadowResult.isNull() ? "no_configurado" : shadowResult["material"] | "no_disponible";
    const float shadowConfidence = shadowResult.isNull() ? 0.0F : shadowResult["confidence"] | 0.0F;
    Serial.printf(
        "foto %u: OpenAI=%s (%.2f) | modelo=%s (%.2f)\n",
        index + 1,
        providerMaterial.c_str(),
        providerConfidence,
        localMaterial.c_str(),
        localConfidence);
    if (shadowMaterial != "no_configurado") {
      Serial.printf("foto %u: modelo sombra=%s (%.2f) [sin voto]\n",
                    index + 1, shadowMaterial.c_str(), shadowConfidence);
    }
    if (index + 1 < kCaptureCount) delay(kCaptureIntervalMs);
  }

  Serial.printf("Votos OpenAI: plastico=%u | vidrio=%u | abstenciones=%u\n",
                providerVotes.plastico, providerVotes.vidrio, providerVotes.abstenciones);
  Serial.printf("Votos modelo: plastico=%u | vidrio=%u | abstenciones=%u\n",
                localVotes.plastico, localVotes.vidrio, localVotes.abstenciones);

  const FinalDecision decision = decideMaterial(providerVotes, localVotes, capturesComplete);
  if (decision.material == "desconocido") {
    Serial.print(F("Resultado: DESCONOCIDO ("));
    Serial.print(decision.source);
    Serial.println(')');
    sendMega("CMD:FACE:confused");
    showOnLcd("No estoy seguro", "Intenta de nuevo");
    return;
  }

  Serial.print(F("Resultado final: "));
  Serial.println(decision.material);
  Serial.print(F("Regla de decision: "));
  Serial.println(decision.source);

  const MaterialVotes& winningVotes = decision.source == "openai_sistema_experto"
      ? providerVotes
      : localVotes;
  const float winningConfidence = decision.material == "plastico"
      ? winningVotes.plasticoConfidence / winningVotes.plastico
      : winningVotes.vidrioConfidence / winningVotes.vidrio;
  const String claimCode = recordRecycleEvent(decision.material, winningConfidence);

  sendMega("CMD:CLASSIFY:" + decision.material);
  sendMega("CMD:FACE:happy");

  if (claimCode.length() > 0) {
    sendMega("CMD:QR:" + claimCode);
    showOnLcd(decision.material == "vidrio" ? "VIDRIO" : "PLASTICO", "Escanea el QR");
  } else if (lastRecycleLinkedToCall) {
    showOnLcd(decision.material == "vidrio" ? "VIDRIO" : "PLASTICO", "10 pts agregados");
  } else {
    showOnLcd(decision.material == "vidrio" ? "VIDRIO" : "PLASTICO", "Compuerta abierta");
  }
}

void readClassificationRequest() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(Serial.read());
    if (command == 'c' || command == 'C') classifyResidue();
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
  dispatcher.begin();
  showOnLcd("Hola, soy Reci", "Envia C para leer");
  sendMega("CMD:FACE:idle");
  Serial.println(F("Listo. Envia C por el Monitor Serial para clasificar un residuo."));
}

void loop() {
  readClassificationRequest();
  dispatcher.tick();
}
