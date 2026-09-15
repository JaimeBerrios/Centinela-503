import serial
import json
import time
import random
import threading
from app.core.config import settings
from app.db.database import insert_sensor_data
from app.services.prediction_service import evaluate_sensor_data

class SerialMonitor:
    def __init__(self):
        self.port = settings.SERIAL_PORT
        self.baudrate = settings.SERIAL_BAUDRATE
        self.timeout = settings.SERIAL_TIMEOUT
        self.is_running = False
        self.thread = None

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()

    def _listen(self):
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"[Serial] Conexión exitosa al hardware en {self.port}")
            while self.is_running:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').strip()
                    self._process_data(line)
        except serial.SerialException:
            print(f"[Serial] ADVERTENCIA: No se encontró {self.port}. Iniciando modo SIMULADOR.")
            self._mock_listen()

    def _mock_listen(self):
        """Genera datos falsos con coordenadas realistas para desarrollo."""
        # Coordenadas base: San Miguel, El Salvador
        base_lat = 13.4833
        base_lon = -88.1833
        
        while self.is_running:
            time.sleep(10)
            
            # Variación para simular nodos dispersos (aprox ±500 metros)
            lat = base_lat + random.uniform(-0.005, 0.005)
            lon = base_lon + random.uniform(-0.005, 0.005)
            
            mock_data = json.dumps({
                "node_id": random.choice([1, 2]),
                "status": random.choice(["Normal", "Emergencia"]),
                "latitude": round(lat, 6),
                "longitude": round(lon, 6)
            })
            print(f"[Simulador] Generado: {mock_data}")
            self._process_data(mock_data)

    def _process_data(self, raw_data: str):
        """Procesa el JSON, evalúa con IA e inyecta en SQLite con GPS."""
        try:
            data = json.loads(raw_data)
            node_id = data.get("node_id")
            status = data.get("status")
            lat = data.get("latitude", 0.0)
            lon = data.get("longitude", 0.0)
            
            if node_id and status:
                priority = evaluate_sensor_data(node_id, status)
                new_id = insert_sensor_data(node_id, status, priority, lat, lon)
                print(f"[Base de Datos] Alerta {new_id} | Nodo {node_id} | IA: {priority} | GPS: {lat}, {lon}")
        except json.JSONDecodeError:
            print(f"[Serial] Error: Trama corrupta recibida -> {raw_data}")

serial_monitor = SerialMonitor()