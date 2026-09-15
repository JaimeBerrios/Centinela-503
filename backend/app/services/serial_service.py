import serial
import json
import time
import random
import threading
from app.core.config import settings
from app.db.database import insert_sensor_data

# ---> NUEVA IMPORTACIÓN <---
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
        """Genera datos falsos para desarrollo cuando no hay ESP32."""
        while self.is_running:
            time.sleep(10)
            mock_data = json.dumps({
                "node_id": random.choice([1, 2]),
                "status": random.choice(["Normal", "Emergencia"])
            })
            print(f"[Simulador] Recibido desde LoRa virtual: {mock_data}")
            self._process_data(mock_data)

    def _process_data(self, raw_data: str):
        """Procesa el JSON, evalúa con IA e inyecta en SQLite."""
        try:
            data = json.loads(raw_data)
            node_id = data.get("node_id")
            status = data.get("status")
            
            if node_id and status:
                # 1. Llamar a la IA para predecir la prioridad
                priority = evaluate_sensor_data(node_id, status)
                
                # 2. Insertar en base de datos incluyendo la predicción
                new_id = insert_sensor_data(node_id, status, priority)
                
                # Modificamos el print para ver el resultado de la IA en tiempo real
                print(f"[Base de Datos] Alerta {new_id} registrada | Estado: {status} | Prioridad IA: {priority}")
        except json.JSONDecodeError:
            print(f"[Serial] Error: Trama corrupta recibida -> {raw_data}")

# Instanciamos el monitor para importarlo en main.py
serial_monitor = SerialMonitor()