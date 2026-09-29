import json
import random
import threading
import serial
from app.core.config import settings
from app.db.database import insert_sensor_data
from app.db import database
from app.services.prediction_service import suggest_triage


class SerialMonitor:
    def __init__(self):
        self.port = settings.SERIAL_PORT
        self.baudrate = settings.SERIAL_BAUDRATE
        self.timeout = settings.SERIAL_TIMEOUT
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.serial_connection = None

    def start(self):
        if self.thread and self.thread.is_alive(): return
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._listen, name="centinela-serial", daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        self.stop_event.set()
        if self.serial_connection:
            try: self.serial_connection.close()
            except serial.SerialException: pass
        if self.thread and self.thread.is_alive(): self.thread.join(timeout=3)

    def _simulation_enabled(self):
        return database.list_policies().get("simulator_enabled", "true").lower() == "true"

    def _listen(self):
        while self.is_running and not self.stop_event.is_set():
            try:
                with serial.Serial(self.port, self.baudrate, timeout=self.timeout) as ser:
                    self.serial_connection = ser
                    print(f"[Serial] Conectado al hardware en {self.port}")
                    while self.is_running and not self.stop_event.is_set():
                        raw = ser.readline()
                        if raw:
                            try: line = raw.decode("utf-8").strip()
                            except UnicodeDecodeError:
                                print("[Serial] Trama descartada: no es UTF-8 válido.")
                                continue
                            self._process_data(line, source="hardware")
                self.serial_connection = None
            except serial.SerialException:
                self.serial_connection = None
                if self._simulation_enabled():
                    print(f"[Serial] Sin hardware en {self.port}; simulador local activo.")
                    self._mock_listen()
                else:
                    print(f"[Serial] Sin hardware en {self.port}; esperando conexión.")
                    self.stop_event.wait(3)
            except Exception as exc:
                print(f"[Serial] Error del monitor: {exc}")
                self.stop_event.wait(2)

    def _mock_listen(self):
        base_lat, base_lon = 13.4833, -88.1833
        descriptions = [
            ("Emergencia", "Se reporta calle inundada cerca del mercado municipal."),
            ("Emergencia", "Árbol caído obstruye parcialmente la vía."),
            ("Emergencia", "Vecinos reportan movimiento sísmico; verificar daños."),
            ("Normal", "Inspección de seguridad del sector completada."),
        ]
        while self.is_running and not self.stop_event.wait(10):
            if not self._simulation_enabled():
                print("[Simulador] Desactivado desde las políticas locales.")
                return
            status, text = random.choice(descriptions)
            payload = {
                "node_id": random.choice((1, 2)),
                "status": status,
                "incident_text": text,
                "latitude": round(base_lat + random.uniform(-0.005, 0.005), 6),
                "longitude": round(base_lon + random.uniform(-0.005, 0.005), 6),
                "source": "simulator",
            }
            self._process_data(json.dumps(payload, ensure_ascii=False), source="simulator")

    def _process_data(self, raw_data: str, source: str = "hardware"):
        try:
            data = json.loads(raw_data)
            node_id = int(data.get("node_id", 0))
            status = str(data.get("status", "")).strip()
            lat = float(data.get("latitude", 0.0))
            lon = float(data.get("longitude", 0.0))
            text = str(data.get("incident_text", ""))[:500]
            if not (1 <= node_id <= 9999) or not status or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                print(f"[Serial] Trama descartada: campos requeridos inválidos -> {raw_data[:160]}")
                return
            suggestion = suggest_triage(text, status)
            new_id = insert_sensor_data(
                node_id, status, "Pendiente", lat, lon, text,
                category=suggestion["category"],
                suggested_priority=suggestion["suggested_priority"],
                suggested_reason=suggestion["basis"],
                triage_state="Pendiente de validación",
                source=data.get("source", source),
            )
            print(f"[Base de Datos] Alerta {new_id} | Nodo {node_id} | Sugerencia: {suggestion['suggested_priority']} | GPS: {lat}, {lon}")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            print(f"[Serial] Trama inválida ({exc}): {raw_data[:160]}")


serial_monitor = SerialMonitor()
