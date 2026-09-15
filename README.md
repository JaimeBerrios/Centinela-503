# 🛡️ Centinela-503

Centinela-503 es un proyecto orientado a la adquisición, procesamiento y análisis de datos provenientes de nodos ESP32/LoRa conectados mediante USB a un servidor local. 

El **Backend Core** actúa como el núcleo de procesamiento, inteligencia artificial y gestión de base de datos. Está construido con una arquitectura limpia, orientada a eventos y aplicando principios DevSecOps.

## 🚀 Características Principales

* **Recepción Asíncrona (PySerial):** Monitor en segundo plano que escucha los datos de los nodos ESP32/LoRa sin bloquear la API principal. Incluye modo simulador automático si no detecta hardware.
* **Agente de Triaje con IA (Scikit-learn):** Implementación de un modelo de Machine Learning (*Decision Tree Classifier*) que evalúa las alertas entrantes en tiempo real para asignar su nivel de prioridad (Alta/Baja) antes de almacenarlas.
* **Agrupación Espacial (Haversine):** Algoritmo matemático que procesa las coordenadas GPS de las alertas y las agrupa en "clústeres" si ocurren a menos de 50 metros de distancia, optimizando la carga de datos para el mapa del frontend.
* **Trazabilidad DevSecOps:** Integración nativa con Azure Boards para el seguimiento automatizado de tareas mediante etiquetas `AB#`.

## 🛠️ Stack Tecnológico

- **Framework Web:** FastAPI (con Uvicorn)
- **Lenguaje / Entorno:** Python 3
- **Base de Datos:** SQLite (Patrón Repositorio)
- **Machine Learning:** Scikit-learn, Numpy
- **Hardware Interfacing:** PySerial, ESP32
- **Sistema Operativo (Recomendado):** Linux Fedora
- **Control de Versiones:** Git

## 📐 Arquitectura General

```text
ESP32 / Nodos LoRa
       │
       │ USB / Serial
       ▼
    PySerial
       │
       ▼
 Serial Service ───────► SQLite
       │
       ▼
 Agente IA (ML)
       │
       ▼
    FastAPI
       │
       ▼
   API REST
       │
       ▼
Cliente / Frontend
```

## 📁 Estructura del Proyecto

```text
Centinela-503/
├── backend/            # Contiene la API, SQLite, comunicación serial y ML
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
├── docs/               # Documentación técnica y definición de la API
├── firmware/           # Código C/C++ ejecutado por el ESP32
├── .gitignore
└── README.md
```

## ⚙️ Guía de Instalación (Para QA y Frontend)

Sigue estos pasos para levantar el servidor localmente con datos simulados o con hardware real.

### 1. Clonar el repositorio
```bash
git clone git@github.com:JaimeBerrios/Centinela-503.git
cd Centinela-503/backend
```

### 2. Configurar el entorno virtual
Es indispensable usar un entorno aislado para no afectar el sistema operativo.

```bash
# Crear entorno virtual
python -m venv .venv

# Activar en Linux/Mac
source .venv/bin/activate

# Activar en Windows
.venv\Scripts\activate
```

### 3. Instalar dependencias
Asegúrate de tener el entorno activado antes de ejecutar esto:

```bash
pip install -r requirements.txt
```

### 4. Levantar el servidor
```bash
uvicorn app.main:app --reload
```
> **Nota:** Al iniciar, el sistema creará la base de datos automáticamente e iniciará el simulador de nodos. Verás los registros de GPS e IA en la terminal.

## 🔌 Comunicación Serial (Hardware Real)
Si conectas un ESP32 real, será detectado normalmente como `/dev/ttyUSB0` o `/dev/ttyACM0`.

El usuario del sistema debe pertenecer al grupo `dialout` en Linux:
```bash
sudo usermod -a -G dialout $USER
```
*No se debe ejecutar el backend como root para acceder al ESP32.*

## 📡 Endpoints Principales

Puedes probar la API directamente desde la documentación interactiva (Swagger) generada automáticamente ingresando a [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) en tu navegador una vez levantado el servidor.

- **`GET /sensors/`**
  Retorna el historial de alertas procesado por el algoritmo espacial. Devuelve un JSON estructurado en clústeres listos para ser consumidos y dibujados en mapas (ej. Leaflet).