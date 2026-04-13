---
layout: home
permalink: index.html

repository-name: e20-co326-Motor-Thermal-Monitoring-Digital-Twin
title: Motor Thermal Monitoring Digital Twin
---

# Motor Health (Thermal) Monitoring Digital Twin

---

## Team
- E/20/037, L.R.H.I. Bandara, [e20037@eng.pdn.ac.lk](mailto:e20037@eng.pdn.ac.lk)
- E/20/363, S.D.Y.V Senanayake, [e20363@eng.pdn.ac.lk](mailto:e20363@eng.pdn.ac.lk)
- E/20/365, C.K. Senaratne, [e20365@eng.pdn.ac.lk](mailto:e20365@eng.pdn.ac.lk)
- E/20/420, J.K. Wanasinghe, [e20420@eng.pdn.ac.lk](mailto:e20420@eng.pdn.ac.lk)

## Supervisor
- Prof. Kamalanath Samarakoon, [kamalanath@eng.pdn.ac.lk](mailto:kamalanath@eng.pdn.ac.lk)

## Tags
- DigitalTwin
- Grafana
- IIOT
- TinyML
- ESP32
- NodeRed
- InfluxDB
- IndustrialSystems
- Automation
- SCADA
- Monitoring

## Table of Contents
1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Links](#links)

---

## Introduction

This project implements an Industrial IoT digital twin for motor health monitoring using a 4-layer edge-to-cloud architecture. The core objective is to detect motor overheating, thermal runaway, and cooling failure using edge-level temperature analytics and cloud-based thermal trend analysis.

## System Overview

The implementation uses the following technology stack:

- Edge Data Source (current): Python mock temperature publisher
- Edge Device (future phase): ESP32-S3 firmware layer
- Message Broker: Eclipse Mosquitto (MQTT + Sparkplug B)
- Flow Logic: Node-RED
- Historian: InfluxDB
- Visualization and Digital Twin: Grafana
- Infrastructure: Docker and Docker Compose

## Links

- [Project Repository](https://github.com/cepdnaclk/{{ page.repository-name }}){:target="_blank"}
- [Project Page](https://cepdnaclk.github.io/{{ page.repository-name }}){:target="_blank"}
- [Department of Computer Engineering](http://www.ce.pdn.ac.lk/)
- [University of Peradeniya](https://eng.pdn.ac.lk/)


[//]: # (Please refer this to learn more about Markdown syntax)
[//]: # (https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
