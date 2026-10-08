import json
import threading
import time
import re
import math
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
        self.recent_alerts = {}

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


    def send_command(self, command: str) -> bool:
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write((command + "\n").encode("utf-8"))
                return True
            except serial.SerialException:
                pass
        return False

    def _listen(self):
        while self.is_running and not self.stop_event.is_set():
            try:
                with serial.Serial(self.port, self.baudrate, timeout=self.timeout) as ser:
                    self.serial_connection = ser
                    print(f"[Serial] Conectado al hardware ESP32 en {self.port}")
                    while self.is_running and not self.stop_event.is_set():
                        raw = ser.readline()
                        if raw:
                            try: line = raw.decode("utf-8", errors="replace").strip()
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

        raw_clean = raw_data.strip()
        if not raw_clean:
            return

        # Match complete protocol messages, never words inside an incident.
        system_message = re.fullmatch(
            r"(?:CLEAR_ALERT|OK|READY|LORA OK|ALERTA LIMPIADA|LIMPIADA|LIMPIAR|"
            r"SILENCIO|(?:ALARMA |BUZZER )?(?:SILENCIAD[OA]|APAGAD[OA])|"
            r"(?:NODO(?: RECEPTOR| EMISOR| \d+)? )?(?:CONECTADO|DESCONECTADO|INICIANDO|READY))"
            r"[.!]?", raw_clean, re.IGNORECASE,
        )
        if system_message:
            return

        # 2. Limpiar caracteres de control espurios de LoRa/Serial
        sanitized = "".join(ch for ch in raw_clean if ch >= " " or ch in "\n\r\t")

        node_id = 1
        status = "Emergencia"
        lat = 13.4833
        lon = -88.1833
        text = ""

        try:
            data = json.loads(sanitized, strict=False)
            if not isinstance(data, dict):
                return
            node_id = int(data.get("node_id", 1))
            status = str(data.get("status", "Emergencia")).strip()
            lat = float(data.get("latitude", 13.4833))
            lon = float(data.get("longitude", -88.1833))
            text = str(data.get("incident_text", "")).strip()[:500]
        except (json.JSONDecodeError, TypeError, ValueError):
            # Si el JSON vino con caracteres corruptos, recuperar campos usando regex
            if "incident_text" in sanitized:
                match_txt = re.search(r'"incident_text"\s*:\s*"([^"]+)"', sanitized)
                if match_txt:
                    text = match_txt.group(1).strip()
                match_id = re.search(r'"node_id"\s*:\s*(\d+)', sanitized)
                if match_id:
                    node_id = int(match_id.group(1))
                match_lat = re.search(r'"latitude"\s*:\s*([-\d.]+)', sanitized)
                if match_lat:
                    try: lat = float(match_lat.group(1))
                    except ValueError: pass
                match_lon = re.search(r'"longitude"\s*:\s*([-\d.]+)', sanitized)
                if match_lon:
                    try: lon = float(match_lon.group(1))
                    except ValueError: pass

            if not text:
                text = sanitized[:500].strip()

        if not text or not (0 <= node_id <= 9999):
            return
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            return
        text = text[:500]

        # 3. Deduplicación inteligente (Debounce de 15s para retransmisiones LoRa o rebote de botón)
        now = time.monotonic()
        self.recent_alerts = {k: ts for k, ts in self.recent_alerts.items() if now - ts < 15.0}

        dedup_key = (source, node_id, status, lat, lon, text.lower())
        if dedup_key in self.recent_alerts:
            elapsed = now - self.recent_alerts[dedup_key]
            print(f"[Serial] Alerta duplicada descartada (recibida hace {elapsed:.1f}s): {text[:45]}...")
            return

        # 4. Triaje local y almacenamiento; deduplicar solo después del commit.
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
            self.recent_alerts[dedup_key] = time.monotonic()
            print(f"[Base de Datos] Alerta {new_id} procesada | Triaje: {suggestion['suggested_priority']}")
        except Exception as e:
            print(f"[Serial] Error guardando la alerta: {e}")

serial_monitor = SerialMonitor()
