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
// La ESP sigue recibiendo eventos del Mega por GPIO13 mediante el divisor.
constexpr int kMegaRxPin = 13;
// GPIO14 deja de ser UART: entrega pulsos largos y robustos hacia Mega D17.
constexpr int kMegaPulsePin = 14;
// UART1 queda solo en sentido Mega -> ESP. El Monitor Serial USB de la ESP
// sigue funcionando a 115200 y no se debe cambiar en Arduino IDE.
constexpr unsigned long kMegaBaud = 4800;
// Cada comando se codifica por la duración HIGH de GPIO14. La separación de
// 300 ms evita que dos pulsos se unan aun cuando el Mega redibuja la OLED.
constexpr unsigned long kPulsoAnalizarMs = 300UL;
constexpr unsigned long kPulsoDesconocidoMs = 600UL;
constexpr unsigned long kPulsoPlasticoMs = 900UL;
constexpr unsigned long kPulsoVidrioMs = 1200UL;
constexpr unsigned long kPulsoP1Ms = 1500UL;
constexpr unsigned long kPulsoP2Ms = 1800UL;
constexpr unsigned long kPulsoSaludoMs = 2100UL;
constexpr unsigned long kPulsoBotellaMs = 2400UL;
constexpr unsigned long kPulsoListoMs = 2700UL;
constexpr unsigned long kPulsoErrorMs = 3000UL;
constexpr unsigned long kPulsoPuntosDirectosMs = 3300UL;
constexpr unsigned long kPulsoPuntosAppMs = 3600UL;
constexpr unsigned long kPulsoGraciasMs = 3900UL;
constexpr unsigned long kPulsoPruebaMs = 4200UL;
constexpr unsigned long kMegaPulseGapMs = 300UL;
// La ESP no registra el reciclaje ni concede puntos hasta que el Mega
// confirme que aceptó la orden de abrir la compuerta.
// Si el Mega ya estaba terminando un pulso de PRESENCIA, la confirmacion de
// compuerta queda en la cola prioritaria. Seis segundos cubren ese caso sin
// repetir la apertura ni cancelar un reciclaje valido.
constexpr unsigned long kCompuertaAckTimeoutMs = 6000UL;
constexpr uint8_t kCompuertaIntentos = 2;
// Protocolo QR por un solo cable GPIO14 -> Mega D17. Un pulso de inicio abre
// la recepción y ocho pulsos siguientes representan 0-9/A-Z. Así el Mega
// puede dibujar el QR real sin depender del UART ruidoso ESP -> Mega.
constexpr unsigned long kPulsoQrInicioMs = 4500UL;
constexpr unsigned long kPulsoQrCaracterBaseMs = 180UL;
constexpr unsigned long kPulsoQrCaracterPasoMs = 60UL;
constexpr unsigned long kPulsoQrInicioGapMs = 240UL;
constexpr unsigned long kPulsoQrCaracterGapMs = 120UL;
constexpr uint8_t kLongitudClaimCode = 8;
constexpr unsigned long kFlashWarmupMs = 220UL;
constexpr unsigned long kCaptureIntervalMs = 350UL;
constexpr unsigned long kWiFiConnectTimeoutMs = 60'000UL;
constexpr unsigned long kClockSyncTimeoutMs = 20000UL;
constexpr uint8_t kClockSyncAttempts = 3;
constexpr uint16_t kVisionHttpTimeoutMs = 60000U;
constexpr int32_t kVisionConnectTimeoutMs = 15000;
constexpr uint16_t kRecycleHttpTimeoutMs = 10000U;
constexpr int32_t kRecycleConnectTimeoutMs = 5000;
constexpr uint8_t kCaptureCount = 3;
constexpr uint8_t kLocalMajorityVotes = (kCaptureCount / 2U) + 1U;
constexpr char kBoundary[] = "ReciMaterialBoundary2026";
constexpr char kVotingPolicy[] = "seis-votos-v3-respaldo-local-mayoria";

void sendMega(const String& command);
bool sendClaimCodeToMega(String claimCode);

HardwareSerial mega(1);
ReciRobotCallDispatcher dispatcher(mega, sendMega);
bool lastRecycleLinkedToCall = false;
bool servicesReady = false;

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

unsigned long pulsoParaComando(const String& command) {
  if (command == "@A") return kPulsoAnalizarMs;
  if (command == "@U") return kPulsoDesconocidoMs;
  if (command == "@P") return kPulsoPlasticoMs;
  if (command == "@V") return kPulsoVidrioMs;
  if (command == "P1") return kPulsoP1Ms;
  if (command == "P2") return kPulsoP2Ms;
  if (command == "@H" || command.startsWith("@G:")) return kPulsoSaludoMs;
  if (command == "@B") return kPulsoBotellaMs;
  if (command == "@S" || command == "@R") return kPulsoListoMs;
  if (command == "@E") return kPulsoErrorMs;
  if (command == "@L") return kPulsoPuntosDirectosMs;
  if (command == "@N" || command.startsWith("@Q:")) return kPulsoPuntosAppMs;
  if (command == "@O") return kPulsoGraciasMs;
  if (command == "@T") return kPulsoPruebaMs;
  return 0;
}

void sendMega(const String& command) {
  const unsigned long duracion = pulsoParaComando(command);
  if (duracion == 0) {
    Serial.print(F("PULSO: orden sin equivalente: "));
    Serial.println(command);
    return;
  }

  digitalWrite(kMegaPulsePin, HIGH);
  delay(duracion);
  digitalWrite(kMegaPulsePin, LOW);
  delay(kMegaPulseGapMs);

  Serial.print(F("MEGA ~> PULSO "));
  Serial.print(command);
  Serial.print(F(" ("));
  Serial.print(duracion);
  Serial.println(F(" ms)"));
}

bool esperarConfirmacionCompuerta() {
  const unsigned long limite = millis() + kCompuertaAckTimeoutMs;
  bool pulsoDetectado = digitalRead(kMegaRxPin) == LOW;

  while (static_cast<long>(millis() - limite) < 0) {
    const bool nivelBajo = digitalRead(kMegaRxPin) == LOW;
    if (nivelBajo) {
      pulsoDetectado = true;
    } else if (pulsoDetectado) {
      Serial.println(F("COMPUERTA: Mega confirmo apertura."));
      return true;
    }
    delay(5);
  }

  Serial.println(F("COMPUERTA: no llego confirmacion del Mega."));
  return false;
}

bool abrirCompuertaConfirmada(const String& material) {
  const String comando = material == "vidrio" ? "@V" : "@P";

  for (uint8_t intento = 1; intento <= kCompuertaIntentos; ++intento) {
    Serial.printf("COMPUERTA: enviando %s, intento %u/%u...\n",
                  material.c_str(), intento, kCompuertaIntentos);
    sendMega(comando);
    if (esperarConfirmacionCompuerta()) return true;
    delay(300);
  }

  return false;
}

void emitirPulsoQr(unsigned long duracion, unsigned long pausa) {
  digitalWrite(kMegaPulsePin, HIGH);
  delay(duracion);
  digitalWrite(kMegaPulsePin, LOW);
  delay(pausa);
}

int indiceCaracterQr(char caracter) {
  if (caracter >= '0' && caracter <= '9') return caracter - '0';
  if (caracter >= 'A' && caracter <= 'Z') return 10 + (caracter - 'A');
  return -1;
}

bool sendClaimCodeToMega(String claimCode) {
  claimCode.trim();
  claimCode.toUpperCase();
  if (claimCode.length() != kLongitudClaimCode) {
    Serial.println(F("QR: claim_code con longitud no compatible."));
    return false;
  }

  uint8_t indices[kLongitudClaimCode] = {};
  for (uint8_t index = 0; index < kLongitudClaimCode; ++index) {
    const int valor = indiceCaracterQr(claimCode[index]);
    if (valor < 0) {
      Serial.println(F("QR: claim_code contiene un caracter no compatible."));
      return false;
    }
    indices[index] = static_cast<uint8_t>(valor);
  }

  // El Mega cambia primero a "Generando QR"; después recibe los 8 símbolos
  // sin redibujar la OLED entre caracteres. Esto evita los caracteres basura
  // que producía el UART directo ESP -> Mega.
  Serial.print(F("QR: enviando codigo real por pulsos: "));
  Serial.println(claimCode);
  emitirPulsoQr(kPulsoQrInicioMs, kPulsoQrInicioGapMs);

  for (uint8_t index = 0; index < kLongitudClaimCode; ++index) {
    const unsigned long duracion = kPulsoQrCaracterBaseMs +
        static_cast<unsigned long>(indices[index]) * kPulsoQrCaracterPasoMs;
    emitirPulsoQr(duracion, kPulsoQrCaracterGapMs);
  }

  Serial.println(F("QR: transferencia terminada; el Mega debe mostrarlo."));
  return true;
}

void showOnLcd(const String& firstLine, const String& secondLine) {
  Serial.print(F("LCD solicitado: "));
  Serial.print(firstLine);
  Serial.print(F(" | "));
  Serial.println(secondLine);
  sendMega("@E");
}

bool synchronizeClockForHttps() {
  for (uint8_t attempt = 1; attempt <= kClockSyncAttempts; ++attempt) {
    Serial.printf("HTTPS: sincronizando reloj (%u/%u)...\n", attempt, kClockSyncAttempts);
    configTime(0, 0, "time.cloudflare.com", "time.google.com", "pool.ntp.org");

    const unsigned long deadline = millis() + kClockSyncTimeoutMs;
    while (time(nullptr) < 1'700'000'000L &&
           static_cast<long>(millis() - deadline) < 0) {
      delay(200);
    }

    if (time(nullptr) >= 1'700'000'000L) {
      Serial.println(F("HTTPS: reloj y certificado listos."));
      return true;
    }
  }

  Serial.println(F("ERROR: no se pudo sincronizar el reloj para HTTPS"));
  showOnLcd("Error de reloj", "Revisa Internet");
  return false;
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
    if (!synchronizeClockForHttps()) return false;
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
  // Render puede estar dormido y la primera inferencia tarda bastante mas
  // que el timeout predeterminado de HTTPClient.
  http.setConnectTimeout(kVisionConnectTimeoutMs);
  http.setTimeout(kVisionHttpTimeoutMs);
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

FinalDecision decideMaterial(const MaterialVotes& providerVotes,
                             const MaterialVotes& localVotes,
                             bool capturesComplete) {
  if (!capturesComplete) return {"desconocido", "respuesta_incompleta"};

  const uint8_t providerValidVotes = providerVotes.plastico + providerVotes.vidrio;
  if (providerValidVotes == 0) {
    if (localVotes.plastico >= kLocalMajorityVotes &&
        localVotes.plastico > localVotes.vidrio) {
      return {"plastico", "modelo_local_mayoria"};
    }
    if (localVotes.vidrio >= kLocalMajorityVotes &&
        localVotes.vidrio > localVotes.plastico) {
      return {"vidrio", "modelo_local_mayoria"};
    }
    return {"desconocido", "modelo_local_sin_mayoria"};
  }

  const uint8_t totalPlastic = providerVotes.plastico + localVotes.plastico;
  const uint8_t totalGlass = providerVotes.vidrio + localVotes.vidrio;
  if (totalPlastic > totalGlass) {
    return {"plastico", "votacion_conjunta"};
  }
  if (totalGlass > totalPlastic) {
    return {"vidrio", "votacion_conjunta"};
  }

  if (providerVotes.plastico > providerVotes.vidrio) {
    return {"plastico", "desempate_openai_sistema_experto"};
  }
  if (providerVotes.vidrio > providerVotes.plastico) {
    return {"vidrio", "desempate_openai_sistema_experto"};
  }
  return {"desconocido", "confusion_sin_resolver"};
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
  http.setConnectTimeout(kRecycleConnectTimeoutMs);
  http.setTimeout(kRecycleHttpTimeoutMs);
  if (!http.begin(client.get(), url)) return "";

  JsonDocument body;
  body["material"] = material;
  body["confidence"] = confidence;
  const bool linkedToCall = dispatcher.addRecycleContext(body);
  String payload;
  serializeJson(body, payload);

  http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
  http.addHeader("Content-Type", "application/json");
  Serial.println(F("RECYCLE: registrando evento en el backend..."));
  const int statusCode = http.POST(payload);
  const String responseBody = statusCode > 0 ? http.getString() : "";
  http.end();

  Serial.printf("RECYCLE: backend respondio %d\n", statusCode);

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
  Serial.print(F("Politica de votacion: "));
  Serial.println(kVotingPolicy);
  sendMega("@A");
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
      const String error = statusCode < 0 ? HTTPClient::errorToString(statusCode) : "HTTP";
      Serial.printf("ERROR: foto %u /vision/classify respondio %d (%s)\n",
                    index + 1, statusCode, error.c_str());
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
          // MobileNetV2 es binario: una abstención local equivale a
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
  Serial.printf("Total conjunto: plastico=%u | vidrio=%u\n",
                providerVotes.plastico + localVotes.plastico,
                providerVotes.vidrio + localVotes.vidrio);

  const FinalDecision decision = decideMaterial(providerVotes, localVotes, capturesComplete);
  if (decision.material == "desconocido") {
    Serial.print(F("Resultado: DESCONOCIDO ("));
    Serial.print(decision.source);
    Serial.println(')');
    sendMega("@U");
    return;
  }

  Serial.print(F("Resultado final: "));
  Serial.println(decision.material);
  Serial.print(F("Regla de decision: "));
  Serial.println(decision.source);

  const bool providerTieBreak = decision.source == "desempate_openai_sistema_experto";
  const uint8_t winningCount = decision.material == "plastico"
      ? (providerTieBreak
          ? providerVotes.plastico
          : providerVotes.plastico + localVotes.plastico)
      : (providerTieBreak
          ? providerVotes.vidrio
          : providerVotes.vidrio + localVotes.vidrio);
  const float winningConfidenceSum = decision.material == "plastico"
      ? (providerTieBreak
          ? providerVotes.plasticoConfidence
          : providerVotes.plasticoConfidence + localVotes.plasticoConfidence)
      : (providerTieBreak
          ? providerVotes.vidrioConfidence
          : providerVotes.vidrioConfidence + localVotes.vidrioConfidence);
  const float winningConfidence = winningCount > 0
      ? winningConfidenceSum / winningCount
      : 0.0F;

  // La operación física ocurre primero. Si el Mega no confirma que aceptó
  // abrir la tapa, no registramos el evento ni entregamos puntos falsos.
  if (!abrirCompuertaConfirmada(decision.material)) {
    Serial.println(F("ERROR: reciclaje cancelado; la compuerta no abrio."));
    sendMega("@E");
    return;
  }

  const String claimCode = recordRecycleEvent(decision.material, winningConfidence);

  if (claimCode.length() > 0) {
    Serial.print(F("RECYCLE: claim_code disponible en backend: "));
    Serial.println(claimCode);
    // Fuera de una llamada, el backend emite un claim_code de un solo uso.
    // Se transmite completo al Mega para que la OLED dibuje el QR real.
    // Solo si el código viniera inválido conservamos el aviso de abrir la app.
    if (!sendClaimCodeToMega(claimCode)) sendMega("@N");
  } else if (lastRecycleLinkedToCall) {
    sendMega("@L");
  } else {
    sendMega("@O");
  }
}

void readClassificationRequest() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(Serial.read());
    if (command == 'c' || command == 'C') {
      classifyResidue();
    } else if (command == 't' || command == 'T') {
      sendMega("@T");
      Serial.println(F("PULSO: prueba enviada al Mega."));
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.println(F("MODO: GPIO14 envia pulsos al Mega D17."));
  // El regreso Mega D16 -> GPIO13 también usa pulsos. Ya no iniciamos UART:
  // GPIO13 queda como entrada digital detrás del divisor 1k/2k.
  pinMode(kMegaRxPin, INPUT);
  pinMode(kMegaPulsePin, OUTPUT);
  digitalWrite(kMegaPulsePin, LOW);
  pinMode(kFlashLedPin, OUTPUT);
  digitalWrite(kFlashLedPin, LOW);
  delay(500);

  Serial.print(F("Firmware de votacion: "));
  Serial.println(kVotingPolicy);
  if (!startCamera()) return;
  if (!connectWiFi()) return;
  dispatcher.begin();
  sendMega("@R");
  servicesReady = true;
  Serial.println(F("Listo. Envia C por el Monitor Serial para clasificar un residuo."));
}

void loop() {
  // Sin hora válida no se verifica TLS; no aceptamos llamadas ni reciclajes
  // hasta que el arranque HTTPS haya terminado correctamente.
  if (!servicesReady) {
    delay(50);
    return;
  }
  readClassificationRequest();
  dispatcher.tick();
  if (dispatcher.takeRecycleRequest()) {
    classifyResidue();
    dispatcher.finishRecycleAttempt();
  }
}
