// Diagnóstico temporal de Wi-Fi para ESP32-CAM.
// No inicializa cámara, no usa credenciales y no transmite datos.

#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  delay(500);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true, true);
  delay(250);

  Serial.println(F("--- ESCANEO WIFI ESP32-CAM ---"));
  const int networks = WiFi.scanNetworks();
  if (networks < 0) {
    Serial.println(F("ERROR: no se pudo escanear redes"));
    return;
  }
  if (networks == 0) {
    Serial.println(F("No se detectaron redes"));
    return;
  }

  Serial.printf("Redes detectadas: %d\n", networks);
  for (int index = 0; index < networks; ++index) {
    Serial.printf("%d. SSID=%s | RSSI=%d dBm | canal=%d | cifrado=%d\n",
                  index + 1,
                  WiFi.SSID(index).c_str(),
                  WiFi.RSSI(index),
                  WiFi.channel(index),
                  WiFi.encryptionType(index));
  }
  WiFi.scanDelete();
  Serial.println(F("Fin del escaneo. Pulsa RST para repetir."));
}

void loop() {}
