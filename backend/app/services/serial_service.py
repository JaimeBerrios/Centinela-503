import json
import threading
import serial
from app.core.config import settings
from app.db.database import insert_sensor_data
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

    def _listen(self):
        while self.is_running and not self.stop_event.is_set():
            try:
                with serial.Serial(self.port, self.baudrate, timeout=self.timeout) as ser:
                    self.serial_connection = ser
                    print(f"[Serial] Conectado al hardware ESP32 en {self.port}")
                    while self.is_running and not self.stop_event.is_set():
                        raw = ser.readline()
                        if raw:
                            try: line = raw.decode("utf-8").strip()
                            except UnicodeDecodeError: continue
                            self._process_data(line, source="hardware")
                self.serial_connection = None
            except serial.SerialException:
                self.serial_connection = None
                print(f"[Serial] Esperando conexión física del ESP32 en {self.port}... (Reintento en 5s)")
                self.stop_event.wait(5)
            except Exception as exc:
                print(f"[Serial] Error del monitor: {exc}")
                self.stop_event.wait(5)

    def _process_data(self, raw_data: str, source: str = "hardware"):
        if not raw_data:
            return
            
        # Ignorar mensajes de inicialización del código de Jefferson
        if "Nodo" in raw_data or "Error" in raw_data:
            print(f"[Serial] Mensaje de sistema: {raw_data}")
            return
            
        # Intentamos leerlo como JSON primero
        try:
            data = json.loads(raw_data)
            node_id = int(data.get("node_id", 1))
            status = str(data.get("status", "Emergencia")).strip()
            lat = float(data.get("latitude", 13.4833))
            lon = float(data.get("longitude", -88.1833))
            text = str(data.get("incident_text", ""))[:500]
        except (json.JSONDecodeError, TypeError, ValueError):
            # ¡Si Jefferson envía solo texto, lo adaptamos automáticamente!
            node_id = 1
            status = "Emergencia"
            # Coordenadas base por defecto (Campus San Miguel)
            lat = 13.4833
            lon = -88.1833
            text = raw_data[:500]
            
        if not text:
            return
            
        try:
            suggestion = suggest_triage(text, status)
            new_id = insert_sensor_data(
                node_id, status, "Pendiente", lat, lon, text,
                category=suggestion["category"],
                suggested_priority=suggestion["suggested_priority"],
                suggested_reason=suggestion["basis"],
                triage_state="Pendiente de validación",
                source=source,
            )
            print(f"[Base de Datos] Alerta {new_id} procesada | Triaje: {suggestion['suggested_priority']}")
        except Exception as e:
            print(f"[Serial] Error guardando la alerta: {e}")

serial_monitor = SerialMonitor()
