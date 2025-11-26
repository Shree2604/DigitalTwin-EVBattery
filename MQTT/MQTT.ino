#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
#include <WiFiSSLClient.h>
#include <ArduinoMqttClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "IIITs";
const char* password = "surya111";

// GitHub CSV details
const char server[] = "media.githubusercontent.com";
const char path[] = "https://media.githubusercontent.com/media/Shree2604/DigitalTwin-EVBattery/refs/heads/main/Dataset/Streaming.csv";

// HiveMQ Cloud MQTT Broker settings
const char* mqttBroker = "02262b1027b44b71baaf077a0855b16f.s1.eu.hivemq.cloud";
const int mqttPort = 8883;
const char* mqttUser = "DigitalTwin-EVBattery";
const char* mqttPass = "Group_07";
const char* mqttTopic = "sensor_data";

// Clients
WiFiSSLClient sslClientCSV;
WiFiSSLClient sslClientMQTT;
HttpClient csvClient(sslClientCSV, server, 443);
MqttClient mqttClient(sslClientMQTT);

bool requestStarted = false;
bool headerSkipped = false;
bool httpHeadersSkipped = false;
unsigned long lastRead = 0;
int rowNumber = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("\nWiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // Connect to MQTT broker
  connectMQTT();
}

void loop() {
  // Keep MQTT connection alive
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.poll();
  
  // CSV Reading Logic
  if (!requestStarted) {
    Serial.println("\n=== Requesting CSV file from GitHub ===");
    csvClient.beginRequest();
    csvClient.get(path);
    csvClient.sendHeader("Host", server);
    csvClient.endRequest();
    
    int status = csvClient.responseStatusCode();
    Serial.print("GitHub Status: ");
    Serial.println(status);
    
    if (status != 200) {
      Serial.println("Failed to download CSV!");
      delay(5000);
      return;
    }
    requestStarted = true;
  }
  
  if (!httpHeadersSkipped) {
    csvClient.skipResponseHeaders();
    httpHeadersSkipped = true;
    Serial.println("HTTP headers skipped!");
  }
  
  if (!headerSkipped) {
    String header = csvClient.readStringUntil('\n');
    Serial.println("CSV Header: " + header);
    Serial.println("Header Skipped.");
    headerSkipped = true;
  }
  
  // Read and publish data every 10 seconds
  if (millis() - lastRead >= 10000) {
    lastRead = millis();
    
    if (csvClient.available()) {
      String line = csvClient.readStringUntil('\n');
      line.trim();
      
      if (line.length() > 5) {
        Serial.println("\n========== ROW " + String(rowNumber) + " ==========");
        parseAndPublish(line);
        rowNumber++;
      } else {
        Serial.println("End of file reached!");
        resetReader();
      }
    } else {
      Serial.println("No more data available!");
      resetReader();
    }
  }
}

void connectMQTT() {
  Serial.print("\nConnecting to HiveMQ Cloud MQTT broker...");
  
  mqttClient.setUsernamePassword(mqttUser, mqttPass);
  
  if (!mqttClient.connect(mqttBroker, mqttPort)) {
    Serial.print("MQTT connection failed! Error code = ");
    Serial.println(mqttClient.connectError());
    Serial.println("Retrying in 5 seconds...");
    delay(5000);
    return;
  }
  
  Serial.println("Connected to HiveMQ Cloud!");
}

void resetReader() {
  requestStarted = false;
  headerSkipped = false;
  httpHeadersSkipped = false;
  rowNumber = 0;
  delay(2000);
}

void parseAndPublish(String row) {
  const int numFields = 25;  
  String fields[numFields];
  int idx = 0;
  
  // Parse CSV row
  while (idx < numFields && row.length() > 0) {
    int pos = row.indexOf(',');
    if (pos == -1) {
      fields[idx++] = row;
      break;
    }
    fields[idx++] = row.substring(0, pos);
    row = row.substring(pos + 1);
  }
  
  if (idx < 25) {
    Serial.println("Incomplete row (got " + String(idx) + " fields), skipping...");
    return;
  }
  
  // Print to Serial
  Serial.println("Timestamp: " + fields[0]);
  Serial.println("SoC: " + fields[1]);
  Serial.println("SoH: " + fields[2]);
  Serial.println("Battery Voltage: " + fields[3] + " V");
  
  // Create JSON with INCREASED buffer size
  StaticJsonDocument<2048> doc;  // INCREASED FROM 1024
  
  doc["timestamp"] = fields[0];
  doc["soc"] = fields[1].toFloat();
  doc["soh"] = fields[2].toFloat();
  doc["battery_voltage"] = fields[3].toFloat();
  doc["battery_current"] = fields[4].toFloat();
  doc["battery_temperature"] = fields[5].toFloat();
  doc["charge_cycles"] = fields[6].toFloat();
  doc["motor_temperature"] = fields[7].toFloat();
  doc["motor_vibration"] = fields[8].toFloat();
  doc["motor_torque"] = fields[9].toFloat();
  doc["motor_rpm"] = fields[10].toFloat();
  doc["power_consumption"] = fields[11].toFloat();
  doc["brake_pad_wear"] = fields[12].toFloat();
  doc["brake_pressure"] = fields[13].toFloat();
  doc["reg_brake_efficiency"] = fields[14].toFloat();
  doc["tire_pressure"] = fields[15].toFloat();
  doc["tire_temperature"] = fields[16].toFloat();
  doc["suspension_load"] = fields[17].toFloat();
  doc["ambient_temperature"] = fields[18].toFloat();
  doc["ambient_humidity"] = fields[19].toFloat();
  doc["load_weight"] = fields[20].toFloat();
  doc["driving_speed"] = fields[21].toFloat();
  doc["distance_traveled"] = fields[22].toFloat();
  doc["idle_time"] = fields[23].toFloat();
  doc["route_roughness"] = fields[24].toFloat();
  doc["row_number"] = rowNumber;
  doc["device_millis"] = millis();
  
  // Serialize with enough space
  String jsonString;
  jsonString.reserve(1024);  // Reserve space
  serializeJson(doc, jsonString);
  
  // Check size before publishing
  Serial.print("JSON size: ");
  Serial.println(jsonString.length());
  
  if (jsonString.length() > 256) {
    Serial.println("WARNING: JSON might be too large for MQTT!");
  }
  
  // Publish to MQTT
  publishToMQTT(jsonString);
}

void publishToMQTT(String payload) {
  Serial.println("\n--- Publishing to MQTT ---");
  
  // Set larger message size if needed
  mqttClient.beginMessage(mqttTopic, payload.length(), false, 0);
  mqttClient.print(payload);
  
  int result = mqttClient.endMessage();
  
  if (result == 1) {
    Serial.println("✓ Published successfully");
  } else {
    Serial.println("✗ Publish failed");
  }
  
  Serial.println("Payload length: " + String(payload.length()));
}