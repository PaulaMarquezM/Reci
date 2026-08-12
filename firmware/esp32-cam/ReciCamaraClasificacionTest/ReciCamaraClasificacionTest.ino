// ============================================================
// RECI · Prueba aislada de cámara + clasificación de residuos
// ESP32-CAM AI Thinker
//
// Este sketch NO se conecta al Mega, NO mueve ruedas, NO abre servos,
// NO registra puntos y NO genera QR. Solo comprueba la cámara, Wi-Fi y
// la API de visión usando tres fotos y una votación segura.
//
// Monitor Serial 115200:
//   C = capturar tres fotos y clasificar
// ============================================================

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include "esp_camera.h"

#include "ReciCamaraClasificacionSecrets.h"

namespace {

// Pines del módulo AI Thinker ESP32-CAM con cámara OV2640.
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

constexpr uint8_t kCaptureCount = 3;
constexpr unsigned long kCaptureIntervalMs = 350UL;
constexpr unsigned long kHttpTimeoutMs = 15000UL;
constexpr char kBoundary[] = "ReciCameraTestBoundary2026";

struct Votes {
  uint8_t plastico = 0;
  uint8_t vidrio = 0;
  float confianzaPlastico = 0;
  float confianzaVidrio = 0;
};

class MultipartCameraStream final : public Stream {
 public:
  MultipartCameraStream(const String& prefix, const uint8_t* image,
                        size_t imageLength, const String& suffix)
      : prefix_(prefix), image_(image), imageLength_(imageLength), suffix_(suffix) {}

  size_t totalLength() const { return prefix_.length() + imageLength_ + suffix_.length(); }
  int available() override { return static_cast<int>(totalLength() - position_); }
  int peek() override { return -1; }
  void flush() override {}
  size_t write(uint8_t) override { return 0; }

  int read() override {
    if (position_ >= totalLength()) return -1;
    const size_t prefixLength = prefix_.length();
    const size_t imageEnd = prefixLength + imageLength_;
    const int value = position_ < prefixLength
        ? static_cast<uint8_t>(prefix_[position_])
        : position_ < imageEnd
          ? image_[position_ - prefixLength]
          : static_cast<uint8_t>(suffix_[position_ - imageEnd]);
    ++position_;
    return value;
  }

 private:
  const String& prefix_;
  const uint8_t* image_;
  size_t imageLength_;
  const String& suffix_;
  size_t position_ = 0;
};

bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print(F("Conectando al Wi-Fi"));
  const unsigned long deadline = millis() + 20000UL;
  while (WiFi.status() != WL_CONNECTED && static_cast<long>(millis() - deadline) < 0) {
    delay(300);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("ERROR: no se pudo conectar al Wi-Fi."));
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
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = psramFound() ? FRAMESIZE_VGA : FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println(F("ERROR: no se pudo iniciar la cámara. Revisa el flex."));
    return false;
  }
  Serial.println(psramFound() ? F("Cámara lista en VGA.") : F("Cámara lista en QVGA (sin PSRAM)."));
  return true;
}

String requestClassification(camera_fb_t* frame, int& statusCode) {
  WiFiClient client;
  HTTPClient http;
  const String url = String(RECI_API_BASE_URL) + "/api/vision/classify";
  String prefix = String("--") + kBoundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"record_event\"\r\n\r\nfalse\r\n--";
  prefix += kBoundary;
  prefix += "\r\nContent-Disposition: form-data; name=\"image\"; filename=\"residuo.jpg\"\r\n";
  prefix += "Content-Type: image/jpeg\r\n\r\n";
  const String suffix = String("\r\n--") + kBoundary + "--\r\n";
  MultipartCameraStream body(prefix, frame->buf, frame->len, suffix);

  if (!http.begin(client, url)) {
    statusCode = -1;
    return "";
  }
  http.setTimeout(kHttpTimeoutMs);
  http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
  http.addHeader("Content-Type", String("multipart/form-data; boundary=") + kBoundary);
  statusCode = http.sendRequest("POST", &body, body.totalLength());
  const String response = statusCode > 0 ? http.getString() : "";
  http.end();
  return response;
}

void addVote(Votes& votes, const String& material, float confidence) {
  if (material == "plastico") {
    ++votes.plastico;
    votes.confianzaPlastico += confidence;
  } else if (material == "vidrio") {
    ++votes.vidrio;
    votes.confianzaVidrio += confidence;
  }
}

String winner(const Votes& votes) {
  if (votes.plastico < 2 && votes.vidrio < 2) return "desconocido";
  if (votes.plastico > votes.vidrio) return "plastico";
  if (votes.vidrio > votes.plastico) return "vidrio";
  return votes.confianzaPlastico >= votes.confianzaVidrio ? "plastico" : "vidrio";
}

void classifyResidue() {
  if (WiFi.status() != WL_CONNECTED && !connectWiFi()) return;

  Serial.println(F("--- CLASIFICACIÓN: tomaré 3 fotos ---"));
  Votes votes;
  for (uint8_t index = 0; index < kCaptureCount; ++index) {
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame == nullptr) {
      Serial.printf("ERROR: no se pudo tomar foto %u\n", index + 1);
      continue;
    }

    Serial.printf("Foto %u: %u bytes. Enviando a visión...\n", index + 1,
                  static_cast<unsigned int>(frame->len));
    int statusCode = 0;
    const String response = requestClassification(frame, statusCode);
    esp_camera_fb_return(frame);

    if (statusCode != HTTP_CODE_OK) {
      Serial.printf("ERROR: visión respondió %d en foto %u.\n", statusCode, index + 1);
      continue;
    }

    JsonDocument document;
    if (deserializeJson(document, response)) {
      Serial.printf("ERROR: respuesta JSON inválida en foto %u.\n", index + 1);
      continue;
    }

    const String material = document["material"].as<String>();
    const float confidence = document["confidence"] | 0.0F;
    addVote(votes, material, confidence);
    Serial.printf("Foto %u: %s (%.0f%%)\n", index + 1, material.c_str(), confidence * 100.0F);
    if (index + 1 < kCaptureCount) delay(kCaptureIntervalMs);
  }

  const String material = winner(votes);
  if (material == "desconocido") {
    Serial.println(F("RESULTADO: DESCONOCIDO. No hubo dos fotos seguras."));
    return;
  }

  const float confidence = material == "plastico"
      ? votes.confianzaPlastico / votes.plastico
      : votes.confianzaVidrio / votes.vidrio;
  Serial.print(F("RESULTADO FINAL: "));
  Serial.print(material);
  Serial.print(F(" (promedio "));
  Serial.print(confidence * 100.0F);
  Serial.println(F("%)"));
  Serial.println(F("Prueba terminada: no se abrió ninguna compuerta ni se dieron puntos."));
}

void readSerial() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(Serial.read());
    if (command == 'C' || command == 'c') classifyResidue();
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  if (!startCamera()) return;
  if (!connectWiFi()) return;
  Serial.println(F("RECI Cámara Test listo."));
  Serial.println(F("Envía C en Monitor Serial 115200 para clasificar un residuo."));
}

void loop() {
  readSerial();
}
