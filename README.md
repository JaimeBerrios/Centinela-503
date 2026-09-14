# Centinela 503

Centinela 503 es un proyecto orientado a la adquisición, procesamiento y análisis de datos provenientes de un ESP32 conectado mediante USB a un servidor local.

El backend está desarrollado en Python y utiliza FastAPI como framework para la API, PySerial para la comunicación con el ESP32, SQLite para persistencia de datos y Scikit-learn para procesamiento y modelos de Machine Learning.

## Stack tecnológico

- Python 3.14
- FastAPI
- Uvicorn
- PySerial
- Scikit-learn
- SQLite
- ESP32
- Linux Fedora
- Git

## Arquitectura general

```text
ESP32
  │
  │ USB / Serial
  ▼
PySerial
  │
  ▼
Serial Service
  │
  ├──────────────► SQLite
  │
  ▼
Procesamiento / Machine Learning
  │
  ▼
FastAPI
  │
  ▼
API REST
  │
  ▼
Cliente / Frontend
Estructura del proyecto
Centinela-503/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── ml/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── data/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── docs/
├── firmware/
├── .gitignore
└── README.md
Componentes principales
Backend

Contiene la API, acceso a SQLite, comunicación serial, procesamiento de datos y Machine Learning.

Firmware

Contendrá el código ejecutado por el ESP32.

Docs

Contiene documentación técnica del proyecto, arquitectura y definición de la API.

Entorno virtual

El entorno virtual del backend se encuentra en:

backend/.venv

No debe almacenarse en Git.

Para activarlo:

cd ~/Proyectos/Centinela-503/backend
source .venv/bin/activate
Dependencias Python

Las dependencias se encuentran en:

backend/requirements.txt

Para instalarlas:

python -m pip install -r requirements.txt
Comunicación serial

El ESP32 será detectado normalmente como:

/dev/ttyUSB0

o:

/dev/ttyACM0

El usuario del sistema debe pertenecer al grupo:

dialout

No se debe ejecutar el backend como root para acceder al ESP32.

Estado inicial

El entorno de desarrollo está preparado y las dependencias principales se encuentran instaladas.

La lógica de negocio y la implementación del backend se desarrollarán posteriormente sobre esta estructura.
