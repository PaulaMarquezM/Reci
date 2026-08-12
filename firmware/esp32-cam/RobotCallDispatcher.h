// ============================================================
// RECI · Despacho de llamadas cloud -> ESP32-CAM -> Arduino Mega
// ============================================================

#ifndef RECI_ROBOT_CALL_DISPATCHER_H
#define RECI_ROBOT_CALL_DISPATCHER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

class ReciRobotCallDispatcher {
 public:
  explicit ReciRobotCallDispatcher(HardwareSerial& mega) : mega_(mega) {}

  void begin() { nextPollAt_ = millis(); }

  void tick() {
    readMegaEvents();

    if (activeCallId_.length() > 0 || WiFi.status() != WL_CONNECTED) return;
    if (static_cast<long>(millis() - nextPollAt_) < 0) return;

    nextPollAt_ = millis() + kPollIntervalMs;
    requestNextCall();
  }

  bool addRecycleContext(JsonDocument& document) {
    if (recycleCallId_.length() == 0 || recyclePointId_.length() == 0) {
      return false;
    }
    if (static_cast<long>(millis() - recycleContextExpiresAt_) >= 0) {
      clearRecycleContext();
      return false;
    }

    document["call_id"] = recycleCallId_;
    document["robot_point_id"] = recyclePointId_;
    return true;
  }

  void clearRecycleContext() {
    recycleCallId_ = "";
    recyclePointId_ = "";
    recycleContextExpiresAt_ = 0;
  }

 private:
  static constexpr unsigned long kPollIntervalMs = 3000UL;
  static constexpr unsigned long kRecycleContextMs = 120000UL;
  // La primera consulta a Next.js en modo desarrollo puede tardar varios
  // segundos mientras compila la ruta. Cinco segundos no siempre alcanzan.
  static constexpr uint16_t kHttpTimeoutMs = 15000;
  static constexpr size_t kMegaEventMaxLength = 48;

  HardwareSerial& mega_;
  String activeCallId_;
  String activePointId_;
  String activeRouteCommand_;
  String activeGreetingName_;
  bool activeCallStarted_ = false;
  String recycleCallId_;
  String recyclePointId_;
  unsigned long recycleContextExpiresAt_ = 0;
  unsigned long nextPollAt_ = 0;
  unsigned long suppressPresenceUntil_ = 0;
  char megaEvent_[kMegaEventMaxLength + 1] = {};
  size_t megaEventLength_ = 0;

  String endpoint(const char* path) const {
    return String(RECI_API_BASE_URL) + path;
  }

  String routeCommandFor(const String& pointName) const {
    String normalized = pointName;
    normalized.trim();
    normalized.toLowerCase();

    if (normalized == "base") return "BASE";
    if (normalized == "p1" || normalized == "parada 1") return "P1";
    if (normalized == "p2" || normalized == "parada 2") return "P2";
    return "";
  }

  String get(const char* path, int& statusCode) {
    WiFiClient client;
    HTTPClient http;
    if (!http.begin(client, endpoint(path))) {
      statusCode = -1;
      return "";
    }
    http.setTimeout(kHttpTimeoutMs);

    http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
    statusCode = http.GET();
    const String response = statusCode > 0 ? http.getString() : "";
    http.end();
    return response;
  }

  bool post(const char* path, const String& body, int& statusCode) {
    WiFiClient client;
    HTTPClient http;
    if (!http.begin(client, endpoint(path))) {
      statusCode = -1;
      return false;
    }
    http.setTimeout(kHttpTimeoutMs);

    http.addHeader("Authorization", String("Bearer ") + RECI_ROBOT_API_KEY);
    http.addHeader("Content-Type", "application/json");
    statusCode = http.POST(body);
    http.end();
    return statusCode >= 200 && statusCode < 300;
  }

  void requestNextCall() {
    int statusCode = 0;
    const String body = get("/api/robot/calls/next", statusCode);
    if (statusCode != HTTP_CODE_OK) {
      Serial.printf("CALLS: /next respondio %d\n", statusCode);
      return;
    }

    JsonDocument document;
    if (deserializeJson(document, body)) {
      Serial.println(F("CALLS: JSON invalido"));
      return;
    }

    JsonVariant call = document["call"];
    if (call.isNull()) return;

    const String callStatus = call["status"] | "";
    if (callStatus != "pending") {
      Serial.println(F("CALLS: hay una ruta en progreso; requiere revisar el Mega."));
      return;
    }

    const String route = routeCommandFor(call["point_name"] | "");
    if (route.length() == 0) {
      Serial.println(F("CALLS: punto sin ruta demo asignada."));
      return;
    }

    activeCallId_ = call["id"] | "";
    activePointId_ = call["point_id"] | "";
    activeRouteCommand_ = route;
    activeGreetingName_ = call["greeting_name"] | "reciclador";
    activeCallStarted_ = false;
    if (activeCallId_.length() == 0 || activePointId_.length() == 0) {
      clearActiveCall();
      Serial.println(F("CALLS: llamada incompleta."));
      return;
    }

    mega_.println(activeRouteCommand_);
    Serial.print(F("MEGA <- ruta: "));
    Serial.println(activeRouteCommand_);
    Serial.print(F("CALLS: saludo al llegar: "));
    Serial.println(activeGreetingName_);
  }

  void updateCall(const char* status) {
    JsonDocument document;
    document["call_id"] = activeCallId_;
    document["status"] = status;
    String body;
    serializeJson(document, body);

    int statusCode = 0;
    if (!post("/api/robot/calls/update", body, statusCode)) {
      Serial.printf("CALLS: update %s respondio %d\n", status, statusCode);
    }
  }

  void reportPosition(const char* status) {
    JsonDocument document;
    document["point_id"] = activePointId_;
    document["status"] = status;
    String body;
    serializeJson(document, body);

    int statusCode = 0;
    if (!post("/api/robot/position", body, statusCode)) {
      Serial.printf("CALLS: position %s respondio %d\n", status, statusCode);
    }
  }

  void processMegaEvent(const char* event) {
    if (strcmp(event, "EVENT:PRESENCE") == 0) {
      if (static_cast<long>(millis() - suppressPresenceUntil_) < 0) return;
      // No se mueve RECI ni se acredita puntos con este evento. Solo se
      // muestra un saludo general para quien se acercó sin usar la app.
      mega_.println(F("CMD:LCD:Hola, soy RECI|Recicla y gana"));
      Serial.println(F("PRESENCE: alguien se acerco a RECI."));
      return;
    }

    if (activeCallId_.length() == 0) return;

    constexpr char kRouteStartedPrefix[] = "EVENT:ROUTE_STARTED:";
    if (!activeCallStarted_ &&
        strncmp(event, kRouteStartedPrefix, strlen(kRouteStartedPrefix)) == 0) {
      activeCallStarted_ = true;
      updateCall("in_progress");
      reportPosition("moving");
      return;
    }

    const String arrived = String("EVENT:ARRIVED:") + activeRouteCommand_;
    if (arrived == event) {
      recycleCallId_ = activeCallId_;
      recyclePointId_ = activePointId_;
      recycleContextExpiresAt_ = millis() + kRecycleContextMs;
      updateCall("resolved");
      reportPosition("idle");
      sendGreeting();
      clearActiveCall();
      return;
    }

    if (strcmp(event, "EVENT:OBSTACLE") == 0) {
      Serial.println(F("CALLS: Mega detenido por obstaculo."));
    }
  }

  void readMegaEvents() {
    while (mega_.available() > 0) {
      const char character = static_cast<char>(mega_.read());
      if (character == '\r') continue;
      if (character == '\n') {
        if (megaEventLength_ > 0) {
          megaEvent_[megaEventLength_] = '\0';
          processMegaEvent(megaEvent_);
          megaEventLength_ = 0;
        }
        continue;
      }

      if (megaEventLength_ >= kMegaEventMaxLength) {
        megaEventLength_ = 0;
        continue;
      }
      megaEvent_[megaEventLength_++] = character;
    }
  }

  void clearActiveCall() {
    activeCallId_ = "";
    activePointId_ = "";
    activeRouteCommand_ = "";
    activeGreetingName_ = "";
    activeCallStarted_ = false;
  }

  void sendGreeting() {
    String name = activeGreetingName_;
    name.replace("\r", "");
    name.replace("\n", "");
    name.replace("|", " ");
    name.trim();
    if (name.length() == 0) name = "reciclador";
    if (name.length() > 18) name.remove(18);

    mega_.print(F("CMD:LCD:Hola, "));
    mega_.print(name);
    mega_.println(F("|Soy RECI"));
    // Mientras la persona que llamó deposita el residuo, el PIR no debe
    // reemplazar su saludo por el mensaje genérico.
    suppressPresenceUntil_ = millis() + 60'000UL;
  }
};

#endif  // RECI_ROBOT_CALL_DISPATCHER_H
