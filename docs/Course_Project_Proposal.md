# Department of Computer Engineering
## CO326 Course Project Proposal (Group Project)
________________________________________
### Industrial Digital Twin & Cyber-Physical Security
**An Edge-to-Cloud Industrial IoT Integration Project**
________________________________________

**Course Level:** 3rd Year Undergraduate Engineering  
**Project Type:** Group Project (3–4 students per group)  
**Project Duration:** 3 Weeks  
**Assessment Weight:** As defined by the course coordinator  

________________________________________

### 1. Introduction
Modern industrial systems are rapidly evolving through the convergence of Operational Technology (OT) and Information Technology (IT). Sensors, controllers, networks, analytics platforms, and cloud systems now operate as a single Cyber-Physical System (CPS). This transformation enables industries to move from reactive maintenance toward predictive and condition-based maintenance, improving reliability, safety, and efficiency.

This project introduces students to Industrial IoT (IIoT) concepts through the design and implementation of a secure Digital Twin system, integrating edge devices, industrial communication protocols, cloud analytics, and visualisation platforms.

Students will work as industrial system integrators, following professional engineering practices rather than experimental or research-oriented approaches.

________________________________________

### 2. Project Objectives
The objectives of this project are to:
1. Design a 4-layer Industrial IoT architecture
2. Implement a secure edge-to-cloud data pipeline
3. Develop a Digital Twin synchronized with a physical system
4. Apply edge-level anomaly detection (TinyML)
5. Perform cloud-based Remaining Useful Life (RUL) estimation
6. Demonstrate bidirectional cyber-physical control
7. Produce industry-standard technical documentation

________________________________________

### 3. Problem Statement

Each group should take one industrial problem (e.g., motor health monitoring, pump cavitation detection, fan imbalance detection). Only one sensor and one actuator should be used. Although a reliable power supply is required for industry applications, this project does not necessitate one unless required by the components.

Although the industrial application differs, all groups must use the same technical framework, architecture, and tools. The course coordinator will provide them. 
The goal is not to build a complex physical machine, but to design a realistic, scalable, and secure industrial monitoring and Digital Twin system.

Although a reliable power supply is required for industry applications, this project does not necessitate one unless required by the components.

________________________________________

### 4. System Overview
The system consists of one sensor and one actuator.

#### 4.1 Physical System
E.g. A small-scale industrial asset instrumented with:
- Current sensing (split-core CT) or Vibration sensing (accelerometer)
- Relay or actuator for control

#### 4.2 Cyber System
- Edge data acquisition and inference
- Secure message transport
- Centralised data historian
- Digital Twin visualization and control

________________________________________

### 5. Mandatory Technology Stack

#### 5.1 Hardware
- ESP32-S3 microcontroller
- Sensor
- Actuator

#### 5.2 Communication & Infrastructure
- MQTT with Sparkplug B topic structure
- Modbus TCP (simulated or real)
- Docker-based deployment

#### 5.3 Software Stack
| Function | Technology |
| --- | --- |
| Edge Logic | ESP32-S3 Firmware |
| Flow Logic | Node-RED |
| Historian | InfluxDB |
| Visualization | Grafana |

Use of alternative platforms is not permitted. Ask the Course Coordinator if you need.

________________________________________

### 6. Industrial IoT Architecture (Mandatory)
Each group must implement the following 4-layer architecture:

**Layer 1 – Perception Layer**
- Sensor data acquisition
- Signal conditioning
- Feature extraction
- Apply Edge AI (TinyML) for real-time anomaly detection

**Layer 2 – Transport Layer**
- MQTT with Sparkplug B
- Structured topic hierarchy (Unified Namespace)

**Layer 3 – Edge-Logic Layer**
- Node-RED data processing
- Rule-based logic
- Analytics orchestration

**Layer 4 – Application Layer**
- Time-series storage
- SCADA-style dashboards
- Digital Twin interface

________________________________________

### 7. Unified Namespace (UNS)
All data must be published using a Unified Namespace.

**Requirements**
- Hierarchical MQTT topics
- Consistent naming
- No hard-coded device dependencies

**Example:**
`spBv1.0/factoryA/DDATA/area1/motor01`

________________________________________

### 8. Digital Twin Requirements

#### 8.1 Digital Twin Definition
The system must implement a true Digital Twin, not merely a dashboard.

| Concept | Requirement |
| --- | --- |
| Digital Model | Static representation |
| Digital Shadow | One-way data synchronization |
| Digital Twin | Bidirectional synchronization |

#### 8.2 Mandatory Features
- Live synchronization with physical system
- Bidirectional control (dashboard → relay)
- Simulation mode (“What-If” scenarios)
- State consistency monitoring

________________________________________

### 9. Machine Learning Requirements

#### 9.1 Edge AI (ESP32-S3)
Each group must implement local anomaly detection at the edge. Use simple ML such as:
- K-Means clustering
- Statistical thresholding
- Lightweight autoencoder (optional)

**Requirements**
- Runs on ESP32-S3
- Real-time inference
- Anomaly score published via MQTT

#### 9.2 Cloud Analytics
A simple Remaining Useful Life (RUL) estimator must be implemented using:
- Linear regression or trend analysis
- Node-RED function nodes

________________________________________

### 10. Cybersecurity & Reliability

**Mandatory Security Features**
- MQTT authentication
- Encrypted credentials
- Controlled topic access

**Mandatory Reliability Features**
- MQTT Last Will & Testament (LWT)
- Local data buffering during outages
- Automatic reconnection
- Timestamped data

________________________________________

### 11. Industrial Implementation Standards

**Mandatory Documentation**
1. System architecture diagram
2. Electrical wiring diagram
3. Simplified P&ID
4. MQTT topic hierarchy
5. Node-RED flow export
6. ML model description
7. Cybersecurity design summary

________________________________________

### 12. Project Timeline 

| Week | Activities |
| --- | --- |
| Week 1 | Architecture, UNS, data flow |
| Week 2 | Edge AI, Digital Twin, dashboards |
| Week 3 | Security, RUL, documentation, demo |

________________________________________

### 13. Assessment Criteria

| Category | Weight |
| --- | --- |
| Firmware Robustness | 20% |
| Network & UNS Design | 20% |
| ML Model Effectiveness | 20% |
| Digital Twin Synchronisation | 20% |
| Documentation & Industrial Quality | 20% |

________________________________________

### 14. Deliverables
Each group must submit:
- Live system demonstration
- Source code (edge + Node-RED) in Github
- Docker configuration
- Final technical report
- Presentation slides

________________________________________

### 16. Expected Learning Outcomes
Upon successful completion, students will be able to:
- Design real-world IIoT systems
- Apply OT/IT convergence principles
- Implement secure cyber-physical systems
- Understand Digital Twin architectures
- Communicate engineering solutions professionally

________________________________________

### 17. Final Note to Students
This project reflects real industrial engineering practice.

Marks are awarded not only for functionality, but for robustness, clarity, and professionalism.

> “A working system is good.
>  A reliable, secure, and well-documented system is industrial-grade.”
