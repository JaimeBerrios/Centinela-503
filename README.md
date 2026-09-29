# 🛡️ Centinela-503

Centinela-503 es un proyecto orientado a la adquisición, procesamiento y análisis de datos provenientes de nodos ESP32/LoRa conectados mediante USB a un servidor local. 

El piloto integra una API local, SQLite, interfaz de coordinación y recepción serial. El sistema está diseñado para mantener la operación dentro de la red local.

## 🚀 Características Principales

* **Recepción local por serial:** El monitor PySerial no bloquea la API. El simulador se puede desactivar desde las políticas institucionales.
* **Triaje explicable:** Reglas locales en español sugieren categoría y prioridad. Coordinación debe validar cada prioridad antes de asignar recursos. Es una línea base; no se presenta como un modelo NLP entrenado.
* **Agrupación espacio-temporal:** Haversine combina proximidad geográfica y un intervalo temporal para reducir reportes duplicados en el mapa local.
* **Control de acceso por rol:** Administrador, Coordinador, Operador de Brigada y Reportante tienen permisos distintos. La cuenta inicial se configura en el primer acceso.
* **Despacho y trazabilidad:** Asignaciones, cambios de estado y decisiones quedan registrados en SQLite; las acciones administrativas se reflejan en una bitácora.

## 🛠️ Stack Tecnológico

- **Framework Web:** FastAPI (con Uvicorn)
- **Lenguaje / Entorno:** Python 3
- **Base de Datos:** SQLite (Patrón Repositorio)
- **Triaje:** Reglas locales explicables; el entrenamiento de un modelo supervisado requiere un conjunto de datos validado.
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
 Sugerencia local
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

Sigue estos pasos para levantar el servidor localmente con el simulador o con hardware real.

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
> **Nota:** En el primer inicio se crea SQLite. Si no se encuentra el puerto serial, el simulador local genera reportes cada 10 segundos, siempre que esa política esté habilitada.

### 5. Abrir el dashboard local

En otra terminal, vuelve a la raíz `Centinela-503` y sirve el directorio frontend:

```bash
python -m http.server 5500 --directory frontend
```

Abre `http://127.0.0.1:5500`. El dashboard consulta `GET /sensors/` y envía reportes a `POST /sensors/`; puedes verificar la API en `http://127.0.0.1:8000/docs`. La URL predeterminada del servidor es `http://127.0.0.1:8000`. CORS permite previews de desarrollo servidos desde `localhost`, `127.0.0.1` o `::1`. Para otra dirección de API, agrega `?api=http://DIRECCION:PUERTO` a la URL del dashboard.

En el primer acceso, crea la cuenta de Administrador Institucional con contraseña de al menos 10 caracteres. Después crea brigadas, coordinadores, operadores y reportantes desde **Usuarios y roles**. Asocia primero una brigada para dar de alta a un Operador de Brigada.

La interfaz muestra una vista previa ilustrativa solo cuando no hay sesión/API; esa vista previa no se guarda ni se envía como información real. El mapa esquemático, estilos e iconos están incluidos localmente.

## 🔌 Comunicación Serial (Hardware Real)
Si conectas un ESP32 real, será detectado normalmente como `/dev/ttyUSB0` o `/dev/ttyACM0`.

El usuario del sistema debe pertenecer al grupo `dialout` en Linux:
```bash
sudo usermod -a -G dialout $USER
```
*No se debe ejecutar el backend como root para acceder al ESP32.*

## 📡 Endpoints principales

Puedes probar la API directamente desde la documentación interactiva (Swagger) generada automáticamente ingresando a [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) en tu navegador una vez levantado el servidor.

- **`POST /auth/setup`**, **`POST /auth/login`**, **`GET /auth/me`**, **`POST /auth/logout`**: configuración del primer administrador y sesiones locales.
- **`GET /sensors/`**, **`POST /sensors/`**: mapa agrupado y registro de reportes.
- **`GET /incidents`**, **`PATCH /incidents/{id}`**: bandeja, validación y cierre de alertas.
- **`GET/POST /brigades/`**, **`PATCH /brigades/{id}`**: administración y disponibilidad.
- **`GET/POST /assignments`**, **`PATCH /assignments/{id}`**: asignación y seguimiento de atención.
- **`GET/POST /decisions`**, **`GET/PATCH /policies`**, **`GET /audit`**, **`GET /users/`**: decisiones, políticas, auditoría y cuentas según rol.

Las rutas completas y sus permisos están descritos en [`docs/api.md`](docs/api.md). Los endpoints requieren token local salvo estado, configuración inicial y login.
