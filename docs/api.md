# API local de Centinela 503

Base local durante desarrollo: `http://127.0.0.1:8000`. La documentación interactiva está en `/docs` y ReDoc en `/redoc`.

Salvo los endpoints públicos indicados, se requiere `Authorization: Bearer <token>`. Las sesiones duran 12 horas. Los passwords se almacenan con PBKDF2-HMAC-SHA256; el token aleatorio se guarda como hash en SQLite.

## Configuración y sesión

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /health/` | Público | Estado del proceso API |
| `GET /auth/setup-status` | Público | Indica si falta crear administrador |
| `POST /auth/setup` | Público, solo mientras no existan usuarios | Crea primer Administrador Institucional y sesión |
| `POST /auth/login` | Público | Inicio de sesión local; limita intentos fallidos |
| `GET /auth/me` | Sesión | Perfil y rol actuales |
| `POST /auth/logout` | Sesión | Revoca el token actual |

La configuración inicial requiere `full_name`, `username` y `password` (mínimo 10 caracteres). No hay cuenta predeterminada.

## Alertas e incidentes

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /sensors/` | Todos los roles | Alertas agrupadas para el mapa; los Reportantes solo ven sus propios reportes |
| `POST /sensors/` | Administrador, Coordinador, Reportante | Recibe `node_id`, `status` (`Emergencia`/`Normal`), `incident_text`, `latitude`, `longitude` |
| `GET /incidents` | Sesión | Bandeja de alertas; Reportantes solo ven las suyas |
| `PATCH /incidents/{id}` | Administrador, Coordinador | Cambia prioridad validada, estado de validación o resolución; registra decisión y auditoría |
| `GET /incidents/{id}/recommendations` | Administrador, Coordinador | Sugiere brigadas disponibles por capacidades y distancia directa |

El registro asigna categoría y **prioridad sugerida** mediante reglas locales transparentes. `priority` permanece `Pendiente` hasta que el Coordinador/Admin la valida. Estas reglas no sustituyen un modelo NLP entrenado ni el criterio del personal. La recomendación de brigada calcula distancia en línea recta, no una ruta vial.

## Brigadas y asignaciones

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /brigades/` | Administrador, Coordinador, Operador de Brigada | Consulta de brigadas y disponibilidad |
| `POST /brigades/` | Administrador | Crea brigada con `name`, `zone`, `skills` y coordenadas opcionales |
| `PATCH /brigades/{id}` | Administrador, Coordinador; Operador solo en su brigada | Actualiza datos; el operador cambia disponibilidad |
| `GET /assignments` | Administrador, Coordinador, Operador | Consulta; el operador solo ve asignaciones de su brigada |
| `POST /assignments` | Administrador, Coordinador | Asigna brigada a alerta validada y disponible |
| `PATCH /assignments/{id}` | Administrador, Coordinador; Operador de la brigada asignada | Cambia a `En camino`, `Atendiendo`, `Completada` o `Cancelada`, respetando transiciones |

Al completar una asignación, el incidente se marca resuelto. Las actualizaciones de campo registran una decisión.

## Decisiones, usuarios y políticas

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /decisions` | Administrador, Coordinador | Cronología de validaciones y despacho |
| `POST /decisions` | Administrador, Coordinador | Registra una decisión manual |
| `GET /users/`, `POST /users/`, `PATCH /users/{id}`, `DELETE /users/{id}` | Administrador | Cuentas, asignación de rol/brigada y desactivación |
| `GET /policies`, `PATCH /policies` | Administrador | Radio espacial y simulador serial de desarrollo |
| `GET /audit` | Administrador | Bitácora de cambios, accesos e intentos fallidos |
| `GET /overview` | Sesión | Resumen operativo aplicado según el rol |

Roles: `admin`, `coordinator`, `brigade_operator`, `reporter`. El backend aplica permisos; ocultar una pantalla no es el único control.

La validación humana de prioridad es obligatoria y no se puede desactivar desde la configuración del piloto.

## Respuesta agrupada del mapa

`GET /sensors/` devuelve `total_raw_alerts`, `total_clusters` y `data`. Cada grupo incluye centro, prioridad (validada o sugerida) y reportes. El agrupamiento usa proximidad Haversine y una ventana temporal de 15 minutos; el radio espacial viene de la política local.
