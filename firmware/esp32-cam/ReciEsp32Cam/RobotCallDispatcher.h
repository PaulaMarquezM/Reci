// ============================================================
// RECI · Despacho de llamadas cloud -> ESP32-CAM -> Arduino Mega
// ============================================================

#ifndef RECI_ROBOT_CALL_DISPATCHER_H
#define RECI_ROBOT_CALL_DISPATCHER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "ReciHttpClient.h"

class ReciRobotCallDispatcher {
 public:
  // En modo demostración las órdenes ESP -> Mega viajan como pulsos GPIO,
  // no como texto UART. El UART queda solo para los eventos Mega -> ESP.
  using MegaCommandSender = void (*)(const String& command);

  explicit ReciRobotCallDispatcher(HardwareSerial& mega,
                                   MegaCommandSender commandSender)
      : mega_(mega), commandSender_(commandSender) {}

  // La demo arranca físicamente en BASE. Primero la publicamos en el mapa y
  // dejamos unos segundos de margen antes de buscar una llamada pendiente.
  void begin() {
    const unsigned long now = millis();
    pinMode(kMegaReturnPulsePin, INPUT);
    megaPulseEnabledAt_ = now + kMegaReturnPulseIgnoreMs;
    megaPulseActive_ = digitalRead(kMegaReturnPulsePin) == LOW;
    if (megaPulseActive_) megaPulseStartedAt_ = now;
    nextBasePositionAt_ = now + kInitialBasePositionDelayMs;
    nextPollAt_ = now + kInitialPollDelayMs;
  }

  void tick() {
    readMegaEvents();
    updateRecyclePreparation();

    if (!basePositionReported_ && WiFi.status() == WL_CONNECTED &&
        static_cast<long>(millis() - nextBasePositionAt_) >= 0) {
      nextBasePositionAt_ = millis() + kPollIntervalMs;
      basePositionReported_ = reportInitialBasePosition();
    }

    if (activeCallId_.length() > 0 || WiFi.status() != WL_CONNECTED) return;
    if (static_cast<long>(millis() - nextPollAt_) < 0) return;

    nextPollAt_ = millis() + kPollIntervalMs;
    requestNextCall();
  }

  bool takeRecycleRequest() {
    if (!recycleRequestPending_ || !recyclePromptShown_) return false;
    if (static_cast<long>(millis() - recycleCaptureAt_) < 0) return false;

    recycleRequestPending_ = false;
    recycleInProgress_ = true;
    return true;
  }

  void finishRecycleAttempt() {
    recycleInProgress_ = false;
    suppressRecycleUntil_ = millis() + kRecycleCooldownMs;
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
  static constexpr unsigned long kInitialBasePositionDelayMs = 500UL;
  static constexpr unsigned long kInitialPollDelayMs = 10000UL;
  static constexpr unsigned long kPollIntervalMs = 3000UL;
  static constexpr unsigned long kRecycleContextMs = 120000UL;
  static constexpr unsigned long kGreetingDurationMs = 1500UL;
  static constexpr unsigned long kBottlePreparationMs = 5000UL;
  static constexpr unsigned long kRecycleCooldownMs = 10000UL;
  // La primera consulta a Next.js en modo desarrollo puede tardar varios
  // segundos mientras compila la ruta. Cinco segundos no siempre alcanzan.
  static constexpr uint16_t kHttpTimeoutMs = 15000;
  // Mega D16 -> divisor -> ESP GPIO13. D16 queda HIGH en reposo y cada
  // evento es un pulso LOW. Usa el mismo cable existente, sin UART.
  static constexpr uint8_t kMegaReturnPulsePin = 13;
  static constexpr unsigned long kMegaArrivalP1PulseMs = 1800UL;
  static constexpr unsigned long kMegaArrivalP2PulseMs = 2400UL;
  static constexpr unsigned long kMegaPresencePulseMs = 3000UL;
  static constexpr unsigned long kMegaPongPulseMs = 3600UL;
  static constexpr unsigned long kMegaReturnPulseToleranceMs = 180UL;
  static constexpr unsigned long kMegaReturnPulseIgnoreMs = 1000UL;

  HardwareSerial& mega_;
  MegaCommandSender commandSender_;
  String activeCallId_;
  String activePointId_;
  String activeRouteCommand_;
  String activeGreetingName_;
  bool activeCallStarted_ = false;
  String recycleCallId_;
  String recyclePointId_;
  unsigned long recycleContextExpiresAt_ = 0;
  unsigned long nextPollAt_ = 0;
  unsigned long nextBasePositionAt_ = 0;
  bool basePositionReported_ = false;
  unsigned long suppressPresenceUntil_ = 0;
  bool recycleRequestPending_ = false;
  bool recyclePromptShown_ = false;
  bool recycleInProgress_ = false;
  unsigned long recyclePromptAt_ = 0;
  unsigned long recycleCaptureAt_ = 0;
  unsigned long suppressRecycleUntil_ = 0;
  bool megaPulseActive_ = false;
  unsigned long megaPulseStartedAt_ = 0;
  unsigned long megaPulseEnabledAt_ = 0;

  void sendMegaCommand(const String& command) {
    if (commandSender_ != nullptr) commandSender_(command);
  }

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
    const String url = endpoint(path);
    ReciHttpClient client(url);
    HTTPClient http;
    if (!http.begin(client.get(), url)) {
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
    const String url = endpoint(path);
    ReciHttpClient client(url);
    HTTPClient http;
    if (!http.begin(client.get(), url)) {
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

  void scheduleRecycle() {
    if (recycleRequestPending_ || recycleInProgress_) return;
    if (static_cast<long>(millis() - suppressRecycleUntil_) < 0) return;

    const unsigned long now = millis();
    recycleRequestPending_ = true;
    recyclePromptShown_ = false;
    recyclePromptAt_ = now + kGreetingDurationMs;
    recycleCaptureAt_ = recyclePromptAt_ + kBottlePreparationMs;
    Serial.println(F("RECYCLE: captura automatica programada."));
  }

  void updateRecyclePreparation() {
    if (!recycleRequestPending_ || recyclePromptShown_) return;
    if (static_cast<long>(millis() - recyclePromptAt_) < 0) return;

    recyclePromptShown_ = true;
    sendMegaCommand("@B");
    Serial.println(F("RECYCLE: captura automatica en 5 segundos."));
  }

  void cancelRecyclePreparation() {
    recycleRequestPending_ = false;
    recyclePromptShown_ = false;
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

    cancelRecyclePreparation();
    sendMegaCommand(activeRouteCommand_);

    // La orden por pulso ya fue enviada al Mega. La app debe reflejarlo en
    // seguida: no esperamos al evento UART de vuelta para marcar una llamada
    // como aceptada ni para mover el marcador del mapa. Los eventos del Mega
    // siguen siendo la fuente que confirma la llegada y marca "idle".
    activeCallStarted_ = true;
    updateCall("in_progress");
    reportPosition("moving");

    Serial.print(F("PULSO -> ruta: "));
    Serial.println(activeRouteCommand_);
    Serial.print(F("CALLS: saludo al llegar: "));
    Serial.println(activeGreetingName_);
    Serial.println(F("CALLS: app actualizada; RECI va en camino."));
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
      return;
    }
    Serial.printf("CALLS: estado -> %s\n", status);
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
      return;
    }
    Serial.printf("CALLS: posicion -> %s\n", status);
  }

  // En el arranque aún no tenemos el UUID de Base, pero el backend lo
  // resuelve por nombre y guarda las coordenadas reales del punto. Esto deja
  // el marcador en Base aun antes de que alguien pulse "Llamar a Reci".
  bool reportInitialBasePosition() {
    JsonDocument document;
    document["point_name"] = "Base";
    document["status"] = "idle";
    String body;
    serializeJson(document, body);

    int statusCode = 0;
    if (!post("/api/robot/position", body, statusCode)) {
      Serial.printf("CALLS: base inicial respondio %d\n", statusCode);
      return false;
    }
    Serial.println(F("CALLS: posicion inicial -> BASE."));
    return true;
  }

  void processMegaEvent(const char* event) {
    Serial.print(F("MEGA -> ESP: "));
    Serial.println(event);

    if (strcmp(event, "PONG") == 0) {
      Serial.println(F("UART: Mega -> ESP OK (PONG recibido)."));
      return;
    }

    constexpr char kAckPrefix[] = "ACK:";
    if (strncmp(event, kAckPrefix, strlen(kAckPrefix)) == 0) {
      Serial.print(F("UART: Mega confirmo "));
      Serial.println(event + strlen(kAckPrefix));
      return;
    }

    if (strcmp(event, "EVENT:PRESENCE") == 0) {
      // El PIR detecta presencia, no identidad ni el residuo. El Mega ya
      // mostró el saludo; aquí programamos la captura para dar tiempo a que
      // la persona ubique la botella frente a la cámara.
      scheduleRecycle();
      if (static_cast<long>(millis() - suppressPresenceUntil_) >= 0) {
        sendMegaCommand("@H");
      }
      Serial.println(F("PRESENCE: alguien se acerco a RECI."));
      return;
    }

    if (activeCallId_.length() == 0) return;

    constexpr char kRouteStartedPrefix[] = "EVENT:ROUTE_STARTED:";
    if (!activeCallStarted_ &&
        strncmp(event, kRouteStartedPrefix, strlen(kRouteStartedPrefix)) == 0) {
      cancelRecyclePreparation();
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
      // Quien llamó ya está esperando en la parada: después del saludo y el
      // mensaje para ubicar la botella, la cámara comienza sola. El PIR sigue
      // sirviendo para reciclajes espontáneos sin una llamada de la app.
      scheduleRecycle();
      clearActiveCall();
      return;
    }

    if (strcmp(event, "EVENT:OBSTACLE") == 0) {
      Serial.println(F("CALLS: Mega detenido por obstaculo."));
    }
  }

  bool matchesMegaPulse(unsigned long duration,
                        unsigned long expected) const {
    const unsigned long minimum = expected > kMegaReturnPulseToleranceMs
        ? expected - kMegaReturnPulseToleranceMs
        : 0;
    return duration >= minimum &&
           duration <= expected + kMegaReturnPulseToleranceMs;
  }

  void processMegaPulse(unsigned long duration) {
    Serial.print(F("MEGA -> ESP: pulso de "));
    Serial.print(duration);
    Serial.println(F(" ms."));

    if (matchesMegaPulse(duration, kMegaArrivalP1PulseMs)) {
      processMegaEvent("EVENT:ARRIVED:P1");
    } else if (matchesMegaPulse(duration, kMegaArrivalP2PulseMs)) {
      processMegaEvent("EVENT:ARRIVED:P2");
    } else if (matchesMegaPulse(duration, kMegaPresencePulseMs)) {
      processMegaEvent("EVENT:PRESENCE");
    } else if (matchesMegaPulse(duration, kMegaPongPulseMs)) {
      processMegaEvent("PONG");
    } else {
      Serial.println(F("MEGA -> ESP: pulso desconocido; ignorado."));
    }
  }

  void readMegaEvents() {
    const bool levelLow = digitalRead(kMegaReturnPulsePin) == LOW;
    const unsigned long now = millis();

    if (static_cast<long>(now - megaPulseEnabledAt_) < 0) {
      megaPulseActive_ = levelLow;
      if (levelLow) megaPulseStartedAt_ = now;
      return;
    }

    if (levelLow && !megaPulseActive_) {
      megaPulseActive_ = true;
      megaPulseStartedAt_ = now;
      return;
    }

    if (!levelLow && megaPulseActive_) {
      megaPulseActive_ = false;
      if (megaPulseStartedAt_ < megaPulseEnabledAt_) return;
      processMegaPulse(now - megaPulseStartedAt_);
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

    // El pulso comunica el saludo genérico; el nombre dinámico no se
    // transmite en esta vía de una sola señal.
    sendMegaCommand(String("@G:") + name);
    // Mientras la persona que llamó deposita el residuo, el PIR no debe
    // reemplazar su saludo por el mensaje genérico.
    suppressPresenceUntil_ = millis() + 60'000UL;
  }
};

#endif  // RECI_ROBOT_CALL_DISPATCHER_H
