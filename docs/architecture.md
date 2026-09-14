# Arquitectura de Centinela 503

## Flujo general

```text
┌───────────────┐
│     ESP32     │
└───────┬───────┘
        │
        │ USB / Serial
        ▼
┌───────────────┐
│   PySerial    │
└───────┬───────┘
        │
        ▼
┌─────────────────────┐
│   Serial Service    │
└─────────┬───────────┘
          │
          ├────────────────► SQLite
          │
          ▼
┌─────────────────────┐
│ Processing / ML     │
│   Scikit-learn      │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│      FastAPI        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│      API REST       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Cliente / Frontend  │
└─────────────────────┘
Estructura del backend
app/main.py

Punto de entrada de la aplicación FastAPI.

Será responsable de crear la aplicación y registrar los routers principales.

app/api/

Contiene la capa HTTP de la aplicación.

router.py

Router principal de FastAPI.

Agrupará los diferentes endpoints disponibles.

routes/health.py

Endpoint para comprobar el estado del backend.

routes/sensors.py

Endpoints relacionados con datos provenientes de sensores.

routes/predictions.py

Endpoints relacionados con resultados o predicciones del modelo de Machine Learning.

app/core/

Configuración general del backend.

config.py

Centralizará configuraciones como:

entorno de ejecución;
puerto serial;
baud rate;
ruta de SQLite;
ubicación del modelo de Machine Learning;
configuración de FastAPI.

Los valores sensibles deberán obtenerse desde variables de entorno.

app/db/

Capa de persistencia.

database.py

Administrará la conexión y operaciones relacionadas con SQLite.

La lógica de acceso a la base de datos deberá mantenerse separada de los endpoints HTTP.

app/schemas/

Contiene los modelos utilizados para validar información.

sensor.py

Schemas relacionados con las lecturas del ESP32.

prediction.py

Schemas relacionados con predicciones o resultados generados por Machine Learning.

app/services/

Contiene la lógica principal de integración.

serial_service.py

Responsable de la comunicación entre Fedora y el ESP32 utilizando PySerial.

Funciones esperadas:

abrir el puerto serial;
cerrar el puerto;
recibir datos;
validar comunicación;
manejar errores de conexión;
entregar los datos a otras capas.
prediction_service.py

Responsable de conectar los datos recibidos con el modelo de Machine Learning.

Debe mantener la lógica del modelo separada de FastAPI.

app/ml/

Contiene los componentes relacionados con Machine Learning.

inference.py

Será responsable de cargar el modelo y ejecutar predicciones.

artifacts/

Directorio destinado a modelos entrenados y artefactos de Machine Learning.

Los modelos generados localmente no deberán almacenarse automáticamente en Git.

backend/data/

Contendrá archivos generados durante la ejecución.

Ejemplo:

centinela503.db

Las bases de datos locales están excluidas de Git.

backend/tests/

Contendrá pruebas automatizadas.

La estructura de pruebas deberá seguir la organización del backend.

Principios de arquitectura

El backend deberá mantener separadas las siguientes responsabilidades:

API
│
├── Validación
│
├── Servicios
│
├── Comunicación Serial
│
├── Persistencia
│
└── Machine Learning

Los endpoints de FastAPI no deberían contener directamente:

operaciones complejas con PySerial;
consultas SQL extensas;
lógica del modelo de IA;
configuración del sistema.

Estas responsabilidades deberán delegarse a los módulos correspondientes.

Seguridad

Centinela 503 deberá seguir como mínimo estos principios:

no ejecutar FastAPI como root;
no almacenar secretos directamente en el código;
utilizar variables de entorno;
no subir archivos .env a Git;
limitar permisos del puerto serial;
utilizar el grupo dialout;
validar los datos recibidos desde el ESP32;
validar las entradas de la API;
evitar confiar directamente en datos provenientes del dispositivo.
