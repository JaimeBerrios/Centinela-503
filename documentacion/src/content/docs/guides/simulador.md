---
title: Código del Simulador de Alertas (Respaldo)
description: Código original de simulación de incidentes para pruebas sin hardware.
---

Si en algún momento el hardware no está disponible y se requiere realizar demostraciones o validaciones de software (QA), se puede reintegrar este código en `backend/app/services/serial_service.py`.

```python
    def _simulation_enabled(self):
        return database.list_policies().get("simulator_enabled", "true").lower() == "true"

    # En el bloque except serial.SerialException de _listen():
    # if self._simulation_enabled():
    #     print(f"[Serial] Desconectado. Simulador activo. Reintentando reconexión en 5s...")
    #     self._mock_listen()

    def _mock_listen(self):
        import random, json
        base_lat, base_lon = 13.4833, -88.1833
        descriptions = [
            ("Emergencia", "Se reporta calle inundada cerca del mercado municipal."),
            ("Emergencia", "Vecinos reportan movimiento sísmico; verificar daños."),
        ]
        # Espera 5s antes de inyectar datos y liberar el hilo para reintentar la conexión
        if not self.stop_event.wait(5):
            if not self._simulation_enabled(): return
            status, text = random.choice(descriptions)
            payload = {
                "node_id": random.choice((1, 2)), "status": status, "incident_text": text,
                "latitude": round(base_lat + random.uniform(-0.005, 0.005), 6),
                "longitude": round(base_lon + random.uniform(-0.005, 0.005), 6),
                "source": "simulator"
            }
            self._process_data(json.dumps(payload, ensure_ascii=False), source="simulator")
```
