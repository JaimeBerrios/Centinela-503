---
title: Arquitectura del Sistema
description: Visión general de la arquitectura de Centinela 503.
---

Centinela 503 está diseñado para operar en condiciones de conectividad nula (filosofía **offline-first**), utilizando una topología descentralizada que no depende de internet.

## Estado de Desarrollo y Componentes

1. **Hardware (En ensamblaje)**
   - **Nodo Emisor (Campo)**: Cuenta con un botón físico de alerta alimentado por batería, programado en C++ sobre un microcontrolador ESP32. Utiliza un transceptor LoRa RFM95 (915MHz) y una antena de 6dBi para máxima penetración y alcance.
   - **Nodo Receptor (Base)**: Recibe las señales RF y está conectado por puerto Serial/USB a la computadora central del centro de operaciones.

2. **Backend (Completado)**
   - El servidor local "escucha" el puerto Serial para atrapar los textos de emergencia que llegan por LoRa.
   - Procesa la información y la clasifica con Inteligencia Artificial utilizando **modelos NLP** para triaje de prioridad y **análisis espacial (DBSCAN)** para agrupar reportes cercanos.
   - Guarda la información procesada en una base de datos **SQLite** y la sirve a través de endpoints RESTful con FastAPI.

3. **Frontend (Completado)**
   - Un panel de control interactivo que grafica los incidentes en el mapa de San Miguel en tiempo real.
   - Permite despachar brigadas y reacciona de forma resiliente mostrando advertencias de "Sin Conexión" si el servidor central se cae, manteniendo en caché la última información vital.
