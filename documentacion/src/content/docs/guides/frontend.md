---
title: Frontend y Dashboard
description: Documentación del panel de control de Centinela 503.
---

La interfaz de usuario web está desarrollada de forma nativa para garantizar rendimiento y compatibilidad sin depender de descargas externas de CDN, respetando el entorno *offline-first*.

## Tecnologías

- **HTML5 y Vanilla JS**: Construcción del núcleo lógico, permitiendo interacciones rápidas y un peso ligero.
- **Tailwind CSS**: Estilización moderna de la interfaz, botones y cuadrículas responsivas.
- **Leaflet.js / SVG**: Despliegue del mapa cartográfico interactivo para la visualización en tiempo real de las incidencias en el Distrito de San Miguel.

## Funcionalidades principales

- **Gestión de Brigadas**: Módulo interactivo para el despliegue y control de recursos de rescate.
- **Consumo de API Segura**: Las peticiones a FastAPI están protegidas mediante el envío de tokens JWT gestionados desde la sesión del usuario.
- **Roles y Operaciones**: Sistema jerárquico de control de acceso.
- **Modo Resiliente**: Si el backend se cae o la red local falla, la interfaz aborta actualizaciones falsas, alerta al coordinador con un indicador visual ("Sin Conexión") y mantiene en pantalla la última imagen táctica disponible para no interrumpir el flujo de rescate.
