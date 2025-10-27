# 🔋 Digital Twin for EV Battery Health & Predictive Maintenance

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Unity](https://img.shields.io/badge/Unity-2021.3+-000000.svg?logo=unity)](https://unity.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Protocol-purple.svg)](https://mqtt.org/)

A comprehensive **Digital Twin–based predictive maintenance system** for Electric Vehicle (EV) batteries that integrates IoT sensors, cloud infrastructure, and AI/ML models. This project creates a virtual replica of physical EV battery behavior using Unity 3D and predicts Remaining Useful Life (RUL) through advanced time-series analysis.

![Digital Twin Architecture](docs/images/architecture-diagram.png)
*System architecture showing IoT-to-Cloud-to-AI pipeline*

## 🎯 Project Overview

This system monitors real-time battery health metrics, predicts degradation patterns, and provides actionable maintenance insights to:
- **Extend battery lifespan** through proactive maintenance
- **Prevent unexpected failures** with early warning systems
- **Optimize EV operations** using data-driven decisions
- **Enable industrial integration** via OPC UA interoperability


## ✨ Key Features

### 🔌 IoT Integration
- **ESP32 sensor nodes** stream live metrics (voltage, temperature, SoC, SoH)
- **MQTT protocol** for lightweight, real-time data transmission
- Configurable sampling rates and alert thresholds

### ☁️ Cloud Connectivity
- Real-time data ingestion and storage
- Support for **AWS IoT Core**, **ThingsBoard**, and **Firebase**
- Scalable architecture for fleet-level monitoring

### 🤖 AI/ML Predictive Models
- **LSTM/GRU networks** for time-series RUL prediction
- **Random Forest & XGBoost** for failure classification
- **SHAP/LIME** for model explainability
- Personalized recommendations based on usage patterns

### 🎮 Digital Twin Visualization
- **Unity 3D** real-time battery replica
- Interactive 3D interface showing health status
- Visual alerts for anomalies and degradation

### ⚙️ Industrial Interoperability
- **OPC UA** server for standardized data access
- Compatible with existing industrial systems
- RESTful APIs for third-party integration

### 📊 Web Dashboard
- Live metrics visualization with historical trends
- Predictive analytics and maintenance schedules
- Customizable alerts and notifications


## 🚀 Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Hardware** | ESP32, Temperature Sensors (DS18B20), Voltage/Current Sensors (INA219) |
| **Protocols** | MQTT, OPC UA, HTTP/REST, WebSocket |
| **Cloud** | AWS IoT Core, Firebase Realtime Database, ThingsBoard |
| **AI/ML** | TensorFlow/Keras (LSTM, GRU), Scikit-learn (RF, XGBoost), SHAP, LIME |
| **Visualization** | Unity 3D (C#), Plotly, Matplotlib |
| **Backend** | Python (Flask/FastAPI), Node.js |
| **Frontend** | Streamlit / React.js |
| **Languages** | Python, C++, C#, JavaScript |
| **DevOps** | Docker, Git, GitHub Actions (CI/CD) |


## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 📧 Contact

For questions or collaboration opportunities:

- **Email**: shree.xai.dev@gmail.com
- **LinkedIn**: [Shreeraj Mummidivarapu](https://linkedin.com/in/m-shreeraj)
- **Project Link**: [https://github.com/Shree2604/DigitalTwin-EVBattery](https://github.com/Shree2604/DigitalTwin-EVBattery)

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ for a sustainable EV future

</div>
