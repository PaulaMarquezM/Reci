// Reci · ESP32-CAM AI Thinker · clasificación de residuos
//
// El Monitor Serial envía C para iniciar una lectura: la cámara toma tres
// fotos con iluminación externa, el backend clasifica cada una y el Mega abre una compuerta
// solo si existe una mayoría segura de plástico o vidrio. El resultado final
// (ya votado) se registra una sola vez en recycle_events; si nadie fue
// identificado, el Mega muestra en el OLED el QR para reclamar los puntos
// desde la app — ver docs/product/DECISION-QR-RECLAMO.md.

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
constexpr uint8_t kCaptureCount = 3;
constexpr char kBoundary[] = "ReciMaterialBoundary2026";

HardwareSerial mega(1);

struct MaterialVotes {
  uint8_t plastico = 0;
  uint8_t vidrio = 0;
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
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print(F("Conectando al Wi-Fi"));
  const unsigned long deadline = millis() + 20'000UL;
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
  config.frame_size = psramFound() ? FRAMESIZE_VGA : FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println(F("ERROR: no se pudo iniciar la cámara"));
    showOnLcd("Error de camara", "Revisa Reci");
    return false;
  }
  Serial.println(psramFound() ? F("Camara en VGA") : F("AVISO: sin PSRAM, camara en QVGA"));
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
  }
}

String winningMaterial(const MaterialVotes& votes) {
  if (votes.plastico < 2 && votes.vidrio < 2) return "desconocido";
  if (votes.plastico > votes.vidrio) return "plastico";
  if (votes.vidrio > votes.plastico) return "vidrio";
  return votes.plasticoConfidence >= votes.vidrioConfidence ? "plastico" : "vidrio";
}

// Registra el resultado final (ya votado) en recycle_events — las 3 fotos
// individuales de arriba usan record_event=false a propósito, para no
// crear tres filas por un solo depósito. Como nadie está identificado
// todavía en este flujo (sin reconocimiento facial aquí), el backend genera
// un claim_code de un solo uso para el QR de puntos — ver
// docs/product/DECISION-QR-RECLAMO.md. Devuelve "" si no hay claim_code (falló el
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

void classifyResidue() {
  if (WiFi.status() != WL_CONNECTED && !connectWiFi()) return;

  Serial.println(F("--- CLASIFICANDO RESIDUO: 3 fotos ---"));
  sendMega("CMD:FACE:thinking");
  showOnLcd("Analizando residuo", "No lo retires");
  MaterialVotes votes;

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
    const String material = document["material"].as<String>();
    const float confidence = document["confidence"] | 0.0F;
    addVote(votes, material, confidence);
    Serial.printf("foto %u: %s (%.2f)\n", index + 1, material.c_str(), confidence);
    if (index + 1 < kCaptureCount) delay(kCaptureIntervalMs);
  }

  const String material = winningMaterial(votes);
  if (material == "desconocido") {
    Serial.println(F("Resultado: DESCONOCIDO (sin mayoria segura)"));
    sendMega("CMD:FACE:confused");
    showOnLcd("No estoy seguro", "Intenta de nuevo");
    return;
  }

  Serial.print(F("Resultado final: "));
  Serial.println(material);

  const float winningConfidence = material == "plastico"
      ? (votes.plastico > 0 ? votes.plasticoConfidence / votes.plastico : 0.0F)
      : (votes.vidrio > 0 ? votes.vidrioConfidence / votes.vidrio : 0.0F);
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
  Serial.println(F("Listo. Envia C por el Monitor Serial para clasificar un residuo."));
}

void loop() {
  readClassificationRequest();
}
