import paho.mqtt.client as mqtt
import json
import numpy as np
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from tensorflow.keras.models import load_model
import pickle
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION ====================

# MQTT Configuration
MQTT_BROKER = "02262b1027b44b71baaf077a0855b16f.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "DigitalTwin-EVBattery"
MQTT_PASS = "Group_07"
MQTT_TOPIC = "sensor_data"

# Firebase Configuration
FIREBASE_CRED_PATH = r"C:\Users\SHREERAJ M\OneDrive\Desktop\DigitalTwin-EVBattery\Firebase\digitaltwin-evbattery-firebase-adminsdk-fbsvc-c087b8aebb.json"
FIREBASE_DB_URL = "https://digitaltwin-evbattery-default-rtdb.firebaseio.com/"

# Model Configuration
MODEL_PATH = "best_rul_model.keras"
PREPROCESSING_PATH = "preprocessing_data.pkl"

# ==================== GLOBAL VARIABLES ====================

model = None
scaler = None
feature_names = []
seq_len = 10
label_encoder = None
data_buffer = deque(maxlen=100)

# Store incomplete messages
message_buffer = ""

# ==================== INITIALIZATION ====================

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DB_URL
        })
        print("✓ Firebase initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Firebase initialization error: {e}")
        return False

def load_rul_model():
    """Load the trained RUL LSTM model and preprocessing data"""
    global model, scaler, feature_names, seq_len, label_encoder
    
    try:
        try:
            model = load_model(MODEL_PATH)
            print(f"✓ Model loaded from {MODEL_PATH}")
        except:
            model_h5 = MODEL_PATH.replace('.keras', '.h5')
            model = load_model(model_h5)
            print(f"✓ Model loaded from {model_h5}")
        
        with open(PREPROCESSING_PATH, 'rb') as f:
            preprocessing_data = pickle.load(f)
        
        scaler = preprocessing_data['scaler']
        feature_names = preprocessing_data['feature_names']
        seq_len = preprocessing_data['seq_len']
        label_encoder = preprocessing_data.get('label_encoder', None)
        
        print(f"✓ Preprocessing data loaded")
        print(f"  Sequence length: {seq_len}")
        print(f"  Number of features: {len(feature_names)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Model loading error: {e}")
        return False

# ==================== MQTT CALLBACKS ====================

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("✓ Connected to HiveMQ Cloud MQTT Broker")
        client.subscribe(MQTT_TOPIC)
        print(f"✓ Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"✗ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Callback when message is received"""
    global message_buffer
    
    try:
        # Get raw message
        raw_message = msg.payload.decode('utf-8', errors='ignore')
        
        # Try to parse as complete JSON first
        try:
            payload = json.loads(raw_message)
            message_buffer = ""  # Clear buffer on success
            process_payload(payload)
            return
        except json.JSONDecodeError:
            # Message might be incomplete, try buffering
            message_buffer += raw_message
            
            # Try to parse buffered message
            try:
                payload = json.loads(message_buffer)
                message_buffer = ""  # Clear buffer on success
                process_payload(payload)
            except json.JSONDecodeError as e:
                # Still incomplete
                if len(message_buffer) > 5000:  # Reset if too large
                    print(f"⚠ Buffer too large, resetting...")
                    message_buffer = ""
                else:
                    print(f"⏳ Buffering message... (size: {len(message_buffer)})")
                
    except Exception as e:
        print(f"✗ Message processing error: {e}")
        import traceback
        traceback.print_exc()
        message_buffer = ""  # Reset on error

def process_payload(payload):
    """Process a complete JSON payload"""
    try:
        print(f"\n{'='*60}")
        print(f"📥 Received data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Row: {payload.get('row_number', 'N/A')}")
        
        # FIX: Display SoC and SoH correctly (multiply by 100 for display)
        soc_display = payload.get('soc', 0) * 100
        soh_display = payload.get('soh', 0) * 100
        print(f"SoC: {soc_display:.2f}%, SoH: {soh_display:.2f}%")
        
        # Process the data
        processed_data = process_incoming_data(payload)
        
        # Add to buffer
        data_buffer.append(processed_data)
        
        # Make RUL prediction if we have enough data
        rul_prediction = None
        prediction_stats = None
        
        if len(data_buffer) >= seq_len:
            rul_prediction, prediction_stats = predict_rul()
            if rul_prediction is not None:
                print(f"🔮 Predicted RUL: {rul_prediction:.2f} cycles")
        else:
            print(f"⏳ Buffering data... ({len(data_buffer)}/{seq_len})")
        
        # Upload to Firebase
        upload_to_firebase(payload, rul_prediction, prediction_stats)
        
    except Exception as e:
        print(f"✗ Payload processing error: {e}")
        import traceback
        traceback.print_exc()

def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker"""
    if rc != 0:
        print(f"⚠ Unexpected disconnection. Reconnecting...")

# ==================== DATA PROCESSING ====================

def process_incoming_data(payload):
    """Process incoming MQTT data to match model's expected format"""
    
    data_dict = {}
    
    feature_mapping = {
        'soc': 'SoC',
        'soh': 'SoH',
        'battery_voltage': 'Battery_Voltage',
        'battery_current': 'Battery_Current',
        'battery_temperature': 'Battery_Temperature',
        'charge_cycles': 'Charge_Cycles',
        'motor_temperature': 'Motor_Temperature',
        'motor_vibration': 'Motor_Vibration',
        'motor_torque': 'Motor_Torque',
        'motor_rpm': 'Motor_RPM',
        'power_consumption': 'Power_Consumption',
        'brake_pad_wear': 'Brake_Pad_Wear',
        'brake_pressure': 'Brake_Pressure',
        'reg_brake_efficiency': 'Reg_Brake_Efficiency',
        'tire_pressure': 'Tire_Pressure',
        'tire_temperature': 'Tire_Temperature',
        'suspension_load': 'Suspension_Load',
        'ambient_temperature': 'Ambient_Temperature',
        'ambient_humidity': 'Ambient_Humidity',
        'load_weight': 'Load_Weight',
        'driving_speed': 'Driving_Speed',
        'distance_traveled': 'Distance_Traveled',
        'idle_time': 'Idle_Time',
        'route_roughness': 'Route_Roughness'
    }
    
    # CRITICAL FIX: Scale percentage values from 0-1 to 0-100
    for payload_key, feature_name in feature_mapping.items():
        if feature_name in feature_names:
            value = payload.get(payload_key, 0.0)
            
            # Convert percentage features from 0-1 scale to 0-100 scale
            # This matches what the model was trained on
            if feature_name in ['SoC', 'SoH', 'Reg_Brake_Efficiency']:
                value = value * 100  # Convert 0.88 to 88
            
            data_dict[feature_name] = value
    
    if 'Timestamp' in feature_names:
        timestamp_str = payload.get('timestamp', '')
        try:
            if timestamp_str:
                timestamp = pd.to_datetime(timestamp_str, format='%d-%m-%Y %H:%M', errors='coerce')
                data_dict['Timestamp'] = timestamp.timestamp() if pd.notna(timestamp) else 0.0
            else:
                data_dict['Timestamp'] = 0.0
        except:
            data_dict['Timestamp'] = 0.0
    
    if 'Maintenance_Type' in feature_names:
        data_dict['Maintenance_Type'] = 0
    
    for feature in feature_names:
        if feature not in data_dict:
            data_dict[feature] = 0.0
    
    feature_values = [data_dict[fname] for fname in feature_names]
    
    return np.array(feature_values)

def predict_rul():
    """Make RUL prediction using the buffered data"""
    try:
        recent_data = list(data_buffer)[-seq_len:]
        
        if len(recent_data) < seq_len:
            return None, None
        
        data_array = np.array(recent_data)
        data_scaled = scaler.transform(data_array)
        X_seq = data_scaled.reshape(1, seq_len, len(feature_names))
        
        prediction = model.predict(X_seq, verbose=0)
        rul_value = float(prediction[0][0])
        
        all_buffer_data = np.array(list(data_buffer))
        buffer_scaled = scaler.transform(all_buffer_data)
        
        recent_predictions = []
        for i in range(len(buffer_scaled) - seq_len + 1):
            seq = buffer_scaled[i:i+seq_len].reshape(1, seq_len, len(feature_names))
            pred = model.predict(seq, verbose=0)[0][0]
            recent_predictions.append(pred)
        
        stats = {
            'current_rul': rul_value,
            'mean_rul': float(np.mean(recent_predictions)) if recent_predictions else rul_value,
            'min_rul': float(np.min(recent_predictions)) if recent_predictions else rul_value,
            'max_rul': float(np.max(recent_predictions)) if recent_predictions else rul_value,
            'std_rul': float(np.std(recent_predictions)) if recent_predictions else 0.0,
            'trend': 'decreasing' if len(recent_predictions) > 1 and recent_predictions[-1] < recent_predictions[0] else 'stable'
        }
        
        return rul_value, stats
        
    except Exception as e:
        print(f"✗ RUL prediction error: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# ==================== FIREBASE OPERATIONS ====================

def upload_to_firebase(payload, rul_prediction, prediction_stats):
    """Upload sensor data and RUL prediction to Firebase Realtime Database"""
    try:
        ref = db.reference('ev_battery_data')
        
        # Convert SoC and SoH to percentage for storage (multiply by 100)
        soc_percent = payload.get('soc', 0) * 100
        soh_percent = payload.get('soh', 0) * 100
        
        data_entry = {
            'timestamp': payload.get('timestamp', ''),
            'device_timestamp': payload.get('device_millis', 0),
            'upload_timestamp': datetime.now().isoformat(),
            'row_number': payload.get('row_number', 0),
            
            'battery': {
                'soc': soc_percent,  # Store as percentage
                'soh': soh_percent,  # Store as percentage
                'voltage': payload.get('battery_voltage', 0),
                'current': payload.get('battery_current', 0),
                'temperature': payload.get('battery_temperature', 0),
                'charge_cycles': payload.get('charge_cycles', 0)
            },
            
            'motor': {
                'temperature': payload.get('motor_temperature', 0),
                'vibration': payload.get('motor_vibration', 0),
                'torque': payload.get('motor_torque', 0),
                'rpm': payload.get('motor_rpm', 0)
            },
            
            'braking': {
                'pad_wear': payload.get('brake_pad_wear', 0),
                'pressure': payload.get('brake_pressure', 0),
                'regen_efficiency': payload.get('reg_brake_efficiency', 0) * 100  # Convert to percentage
            },
            
            'tires': {
                'pressure': payload.get('tire_pressure', 0),
                'temperature': payload.get('tire_temperature', 0)
            },
            
            'vehicle': {
                'power_consumption': payload.get('power_consumption', 0),
                'suspension_load': payload.get('suspension_load', 0),
                'load_weight': payload.get('load_weight', 0),
                'driving_speed': payload.get('driving_speed', 0),
                'distance_traveled': payload.get('distance_traveled', 0),
                'idle_time': payload.get('idle_time', 0)
            },
            
            'environment': {
                'ambient_temperature': payload.get('ambient_temperature', 0),
                'ambient_humidity': payload.get('ambient_humidity', 0),
                'route_roughness': payload.get('route_roughness', 0)
            },
            
            'rul_prediction': {
                'value': rul_prediction if rul_prediction is not None else None,
                'buffer_size': len(data_buffer),
                'required_sequence_length': seq_len,
                'model_type': 'LSTM_RUL',
                'statistics': prediction_stats if prediction_stats else None,
                'health_status': get_health_status(rul_prediction, soh_percent) if rul_prediction else None
            }
        }
        
        new_ref = ref.push(data_entry)
        print(f"✓ Data uploaded to Firebase with key: {new_ref.key}")
        
        latest_ref = db.reference('ev_battery_data/latest')
        latest_ref.set(data_entry)
        
        if rul_prediction is not None and rul_prediction < 100:
            alert_ref = db.reference('alerts')
            alert_ref.push({
                'timestamp': datetime.now().isoformat(),
                'type': 'low_rul',
                'severity': 'critical' if rul_prediction < 5 else 'warning',
                'message': f'Low RUL detected: {rul_prediction:.2f} cycles',
                'rul': rul_prediction,
                'soh': soh_percent,
                'data_key': new_ref.key
            })
            print(f"⚠ Alert created for low RUL: {rul_prediction:.2f}")
        
    except Exception as e:
        print(f"✗ Firebase upload error: {e}")
        import traceback
        traceback.print_exc()

def get_health_status(rul, soh):
    """Determine health status based on RUL and SoH"""
    if rul is None:
        return 'unknown'
    
    if rul > 5 and soh > 80:
        return 'excellent'
    elif rul > 3 and soh > 60:
        return 'good'
    elif rul > 1 and soh > 40:
        return 'fair'
    elif rul > 0.5:
        return 'poor'
    else:
        return 'critical'

# ==================== MAIN FUNCTION ====================

def main():
    """Main function to run the MQTT subscriber"""
    print("\n" + "="*60)
    print("🚗 EV Battery Digital Twin - RUL Prediction System")
    print("="*60 + "\n")
    
    if not initialize_firebase():
        print("⚠ Firebase initialization failed. Exiting...")
        return
    
    if not load_rul_model():
        print("⚠ RUL model loading failed. Exiting...")
        return
    
    # Increase max packet size for MQTT
    client = mqtt.Client(client_id="rul_prediction_subscriber", protocol=mqtt.MQTTv311)
    client.max_inflight_messages_set(20)
    client.max_queued_messages_set(0)
    
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    print(f"🔌 Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("🔄 Starting MQTT loop...")
        print(f"📊 Waiting for {seq_len} samples before making predictions...\n")
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n⏹ Stopping subscriber...")
        client.disconnect()
        print("✓ Disconnected successfully")
    except Exception as e:
        print(f"✗ Connection error: {e}")

if __name__ == "__main__":
    main()  