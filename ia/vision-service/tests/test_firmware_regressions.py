"""Guardas estáticas para funciones del robot que visión no debe reemplazar."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
ESP_DIR = REPO / "firmware" / "esp32-cam" / "ReciEsp32Cam"
MEGA_PATH = REPO / "firmware" / "arduino-mega" / "ReciRutaDemo" / "ReciRutaDemo.ino"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_fragments(text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    assert not missing, f"Regresiones detectadas; faltan: {missing}"


def test_esp32_conserva_https_ntp_camara_y_tres_capturas():
    sketch = _read(ESP_DIR / "ReciEsp32Cam.ino")
    http_client = _read(ESP_DIR / "ReciHttpClient.h")

    _assert_fragments(
        sketch,
        (
            '#include "ReciHttpClient.h"',
            "ReciHttpClient client(url);",
            'startsWith("https://")',
            'configTime(0, 0, "pool.ntp.org", "time.google.com")',
            "kClockSyncTimeoutMs",
            "constexpr uint8_t kCaptureCount = 3;",
            "config.frame_size = FRAMESIZE_QVGA;",
            'Serial.printf("Sensor de camara detectado: PID=0x%04X',
            "for (uint8_t index = 0; index < kCaptureCount; ++index)",
        ),
    )
    _assert_fragments(
        http_client,
        (
            "WiFiClientSecure.h",
            "BEGIN CERTIFICATE",
            "secureClient_.setCACert(kReciTlsRootCa);",
            "NetworkClientSecure secureClient_;",
        ),
    )


def test_esp32_conserva_llamadas_contexto_puntos_y_qr():
    sketch = _read(ESP_DIR / "ReciEsp32Cam.ino")
    dispatcher = _read(ESP_DIR / "RobotCallDispatcher.h")

    _assert_fragments(
        sketch,
        (
            "ReciRobotCallDispatcher dispatcher(mega);",
            "dispatcher.addRecycleContext(body)",
            "dispatcher.clearRecycleContext();",
            'sendMega("CMD:QR:" + claimCode);',
            "dispatcher.begin();",
            "dispatcher.tick();",
            'String(RECI_API_BASE_URL) + "/api/events/recycle"',
        ),
    )
    _assert_fragments(
        dispatcher,
        (
            'get("/api/robot/calls/next", statusCode)',
            'post("/api/robot/calls/update", body, statusCode)',
            'post("/api/robot/position", body, statusCode)',
            'document["call_id"] = recycleCallId_;',
            'document["robot_point_id"] = recyclePointId_;',
            'constexpr char kRouteStartedPrefix[] = "EVENT:ROUTE_STARTED:";',
            'const String arrived = String("EVENT:ARRIVED:") + activeRouteCommand_;',
            'strcmp(event, "EVENT:OBSTACLE") == 0',
            'mega_.println(F("CMD:LCD:Hola, soy RECI|Recicla y gana"));',
        ),
    )


def test_desconocido_retorna_antes_del_unico_cmd_classify():
    sketch = _read(ESP_DIR / "ReciEsp32Cam.ino")
    guard = sketch.index("if (!reci_vision::shouldSendClassify(decision))")
    command = 'sendMega(String("CMD:CLASSIFY:") + decisionMaterial);'
    command_position = sketch.index(command)

    assert sketch.count("CMD:CLASSIFY:") == 1
    assert guard < sketch.index("return;", guard) < command_position
    assert "CMD:CLASSIFY:desconocido" not in sketch


def test_mega_conserva_pines_calibraciones_y_bloqueos_de_seguridad():
    mega = _read(MEGA_PATH)

    _assert_fragments(
        mega,
        (
            "constexpr uint8_t kIzqIn1 = 5;",
            "constexpr uint8_t kIzqIn2 = 6;",
            "constexpr uint8_t kIzqIn3 = 7;",
            "constexpr uint8_t kIzqIn4 = 8;",
            "constexpr uint8_t kDerIn1 = 9;",
            "constexpr uint8_t kDerIn2 = 10;",
            "constexpr uint8_t kDerIn3 = 11;",
            "constexpr uint8_t kDerIn4 = 13;",
            "constexpr bool kInvertirLadoIzquierdo = true;",
            "constexpr uint8_t kServoVidrioPin = 3;",
            "constexpr uint8_t kServoPlasticoPin = 4;",
            "constexpr uint8_t kVidrioCerrado = 45;",
            "constexpr uint8_t kVidrioAbierto = 166;",
            "constexpr uint8_t kPlasticoCerrado = 30;",
            "constexpr uint8_t kPlasticoAbierto = 180;",
            "constexpr unsigned long kCompuertaAbiertaMs = 2000UL;",
            "constexpr uint8_t kTrigFrontal = 22;",
            "constexpr uint8_t kEchoFrontal = 23;",
            "constexpr uint8_t kPirPin = 28;",
            "constexpr unsigned long kBaseAP1Ms = 8000UL;",
            "constexpr unsigned long kP1AP2Ms = 8000UL;",
            "constexpr unsigned long kSerialBaud = 9600UL;",
            "constexpr uint8_t kDireccionOled = 0x3C;",
            "constexpr uint8_t kDireccionLcd = 0x27;",
        ),
    )
    _assert_fragments(
        mega,
        (
            "if (modo != Modo::Detenido)",
            "if (compuertaActiva != CompuertaActiva::Ninguna)",
            "servoPlastico.write(kPlasticoCerrado);",
            "servoVidrio.write(kVidrioCerrado);",
            "actualizarCompuerta();",
            "SEGURIDAD: ruta en espera hasta cerrar la compuerta.",
            "SEGURIDAD: movimiento bloqueado; hay una compuerta abierta.",
            'es(entrada, "CMD:CLASSIFY:vidrio")',
            'es(entrada, "CMD:CLASSIFY:plastico")',
            'emitirEvento(F("ROUTE_STARTED"), proximo);',
            'emitirEvento(F("ARRIVED"), puntoActual);',
            'Serial2.println(F("EVENT:OBSTACLE"));',
        ),
    )
    assert "CMD:CLASSIFY:desconocido" not in mega
