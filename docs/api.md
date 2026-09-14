# API - Centinela 503

Este documento define inicialmente las áreas que tendrá la API.

La implementación definitiva podrá cambiar durante el desarrollo.

## Health

Ruta prevista:

```text
GET /health

Objetivo:

Comprobar que el backend se encuentra funcionando.

Sensores

Rutas previstas:

GET /sensors
GET /sensors/latest

Objetivo:

Consultar información proveniente de los sensores conectados al ESP32.

Predicciones

Ruta prevista:

POST /predictions

Objetivo:

Procesar información mediante el modelo de Machine Learning y devolver el resultado correspondiente.

Documentación automática

FastAPI permitirá posteriormente acceder a:

/docs

para Swagger UI.

Y:

/redoc

para ReDoc.

Las rutas definitivas deberán documentarse conforme avance la implementación.
