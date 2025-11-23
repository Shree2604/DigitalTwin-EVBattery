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
const char path[] = "https://media.githubusercontent.com/media/Shree2604/DigitalTwin-EVBattery/refs/heads/main/Dataset/Dataset.csv";

// HiveMQ Cloud MQTT Broker settings
const char* mqttBroker = "02262b1027b44b71baaf077a0855b16f.s1.eu.hivemq.cloud";
const int mqttPort = 8883;  // TLS port
const char* mqttUser = "DigitalTwin-EVBattery";
const char* mqttPass = "Group_07";
const char* mqttTopic = "sensor_data";  // Topic to publish sensor data

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
  
  // Read and publish data every 3 seconds
  if (millis() - lastRead >= 3000) {
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
  
  // Set username and password
  mqttClient.setUsernamePassword(mqttUser, mqttPass);
  
  // Connect with TLS
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
  delay(2000);  // Wait before restarting
}

void parseAndPublish(String row) {
  // CSV Format: Timestamp,Battery_Temperature,Charge_Cycles,Route_Roughness,Motor_Torque,Reg_Brake_Efficiency
  const int numFields = 6;  
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
  
  // Check if we have all fields
  if (idx < 6) {
    Serial.println("Incomplete row, skipping...");
    return;
  }
  
  // Print to Serial
  Serial.println("Timestamp: " + fields[0]);
  Serial.println("Battery Temperature: " + fields[1] + "°C");
  Serial.println("Charge Cycles: " + fields[2]);
  Serial.println("Route Roughness: " + fields[3]);
  Serial.println("Motor Torque: " + fields[4] + " Nm");
  Serial.println("Reg Brake Efficiency: " + fields[5]);
  
  // Create JSON payload
  StaticJsonDocument<512> doc;
  doc["timestamp"] = fields[0];
  doc["battery_temperature"] = fields[1].toFloat();
  doc["charge_cycles"] = fields[2].toFloat();
  doc["route_roughness"] = fields[3].toFloat();
  doc["motor_torque"] = fields[4].toFloat();
  doc["reg_brake_efficiency"] = fields[5].toFloat();
  doc["row_number"] = rowNumber;
  doc["device_millis"] = millis();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Publish to MQTT
  publishToMQTT(jsonString);
}

void publishToMQTT(String payload) {
  Serial.println("\n--- Publishing to MQTT ---");
  
  mqttClient.beginMessage(mqttTopic);
  mqttClient.print(payload);
  mqttClient.endMessage();
  
  Serial.println("Published to HiveMQ topic: " + String(mqttTopic));
  Serial.println("Payload: " + payload);
}