---
title: Backend (FastAPI)
description: Documentación técnica del servidor y la API REST.
---

El backend está construido con Python 3 y FastAPI.

## Estructura

- `app/api/`: Rutas RESTful (`/auth`, `/sensors`, `/incidents`, `/brigades`).
- `app/core/`: Configuración del entorno (`config.py`) y seguridad (JWT).
- `app/db/`: Inicialización de SQLite y esquemas de base de datos.
- `app/ml/`: Modelos de Machine Learning para clasificar emergencias.
- `app/services/`: Servicios en segundo plano, como el `serial_service.py` que lee los puertos USB o activa el simulador.

## Ejecución

El backend se ejecuta utilizando `uvicorn`:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
