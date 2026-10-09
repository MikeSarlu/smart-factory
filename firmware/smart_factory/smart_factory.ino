#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <math.h>
#include "amazon_root_ca.h"

// ESP32 clasico (WROOM-32 / ESP32 Dev Module); Wi-Fi de 2.4 GHz.
const char* WIFI_SSID = "prueba";
const char* WIFI_PASSWORD = "prueba123";
const bool USE_LOCAL_SERVER = false;
const char* AWS_API_BASE_URL = "https://wrsbsxcc03.execute-api.us-east-2.amazonaws.com/prod";
const char* LOCAL_API_BASE_URL = "http://10.42.0.1:8080";
const char* DEVICE_ID = "esp32_motor_node_01";
const uint8_t PIN_ADC = 34;  // ADC1: compatible con Wi-Fi.
const uint8_t LED_PINS[] = {2, 4}; // led1 integrado; led2 externo con resistencia.
const char* LED_IDS[] = {"led1", "led2"};
const float DIVIDER_FACTOR = 5.0f;
const uint32_t TELEMETRY_INTERVAL = 2000;
const uint32_t CONTROL_INTERVAL = 4000;
const uint32_t WIFI_RETRY_INTERVAL = 15000;
uint32_t lastTelemetry = 0, lastControl = 0, lastWifiRetry = 0;
bool wasConnected = false;

String apiBase() {
  return USE_LOCAL_SERVER ? LOCAL_API_BASE_URL : AWS_API_BASE_URL;
}

bool beginRequest(HTTPClient& http, WiFiClient& plain,
                  WiFiClientSecure& secure, const String& url) {
  http.setConnectTimeout(3000);
  http.setTimeout(3000);
  if (USE_LOCAL_SERVER) return http.begin(plain, url);
  secure.setCACert(AMAZON_ROOT_CA1);
  secure.setHandshakeTimeout(5);
  return http.begin(secure, url);
}

float readMotorVoltage() {
  uint32_t totalMv = 0;
  for (int i = 0; i < 10; ++i) {
    totalMv += analogReadMilliVolts(PIN_ADC);
    delay(2);
  }
  const float voltage = totalMv / 10000.0f * DIVIDER_FACTOR;
  return voltage < 0.15f ? 0.0f : roundf(voltage * 100.0f) / 100.0f;
}

void sendTelemetry() {
  // No guardar fechas ficticias. El control sigue funcionando sin NTP.
  time_t now = time(nullptr);
  if (now < 1704067200) {
    Serial.println("[NTP] Sin hora UTC valida; telemetria pendiente.");
    return;
  }
  struct tm utc;
  gmtime_r(&now, &utc);
  char timestamp[25];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);

  StaticJsonDocument<512> doc;
  doc["timestamp"] = timestamp;
  doc["device_id"] = DEVICE_ID;
  const float voltage = readMotorVoltage();
  JsonObject data = doc.createNestedObject("telemetry");
  data["analog_ch1"] = voltage;
  data["analog_ch2"] = 0.0;
  data["digital_ch1"] = voltage > 1.0f ? 1 : 0;
  data["digital_ch2"] = 0;
  data["digital_ch3"] = voltage > 13.5f ? 1 : 0;
  data["digital_ch4"] = 0;
  data["digital_ch5"] = 0;
  if (doc.overflowed()) {
    Serial.println("[JSON] Capacidad insuficiente; envio cancelado.");
    return;
  }
  String body;
  serializeJson(doc, body);
  WiFiClient plain;
  WiFiClientSecure secure;
  HTTPClient http;
  if (!beginRequest(http, plain, secure, apiBase() + "/telemetry")) {
    Serial.println("[HTTP] No se pudo iniciar telemetria.");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  int status = http.POST(body);
  if (status >= 200 && status < 300) {
    Serial.printf("[TELEMETRIA] OK (%d) %s\n", status, body.c_str());
  } else if (status > 0) {
    Serial.printf("[TELEMETRIA] Error HTTP %d: %s\n", status, http.getString().c_str());
  } else {
    Serial.printf("[TELEMETRIA] Error de red: %s\n", http.errorToString(status).c_str());
  }
  http.end();
}

void pollControl(size_t index) {
  String url = apiBase() + (USE_LOCAL_SERVER ? "/control/status/" : "/control?led_id=") + LED_IDS[index];
  WiFiClient plain;
  WiFiClientSecure secure;
  HTTPClient http;
  if (!beginRequest(http, plain, secure, url)) {
    Serial.println("[CONTROL] No se pudo iniciar peticion.");
    return;
  }
  int status = http.GET();
  if (status == HTTP_CODE_OK) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, http.getString());
    if (error || !doc["state"].is<int>() ||
        (doc["state"].as<int>() != 0 && doc["state"].as<int>() != 1) ||
        String(doc["led_id"] | "") != LED_IDS[index]) {
      Serial.printf("[CONTROL] Respuesta invalida para %s; GPIO sin cambios.\n", LED_IDS[index]);
    } else {
      int state = doc["state"].as<int>();
      digitalWrite(LED_PINS[index], state ? HIGH : LOW);
      Serial.printf("[CONTROL] %s=%d\n", LED_IDS[index], state);
    }
  } else {
    Serial.printf("[CONTROL] Error %d para %s\n", status, LED_IDS[index]);
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  for (uint8_t pin : LED_PINS) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_ADC, ADC_11db);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  Serial.printf("[WIFI] Conectando a %s...\n", WIFI_SSID);
}

void loop() {
  uint32_t now = millis();
  if (WiFi.status() != WL_CONNECTED) {
    wasConnected = false;
    if (now - lastWifiRetry >= WIFI_RETRY_INTERVAL) {
      lastWifiRetry = now;
      Serial.println("[WIFI] Reintentando conexion...");
      WiFi.reconnect();
    }
    delay(10);
    return;
  }
  if (!wasConnected) {
    wasConnected = true;
    Serial.printf("[WIFI] Conectado: %s\n", WiFi.localIP().toString().c_str());
  }
  if (now - lastTelemetry >= TELEMETRY_INTERVAL) {
    lastTelemetry = now;
    sendTelemetry();
  }
  if (millis() - lastControl >= CONTROL_INTERVAL) {
    lastControl = millis();
    for (size_t i = 0; i < 2; ++i) pollControl(i);
  }
  delay(10);
}
