import joblib
import numpy as np
import os
from app.core.config import settings

class TriageModel:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Carga el modelo pre-entrenado desde el disco."""
        try:
            if os.path.exists(settings.MODEL_PATH):
                self.model = joblib.load(settings.MODEL_PATH)
                print(f"[ML] Modelo cargado exitosamente desde {settings.MODEL_PATH}")
            else:
                print(f"[ML] ADVERTENCIA: No se encontró el modelo en {settings.MODEL_PATH}")
        except Exception as e:
            print(f"[ML] Error crítico cargando el modelo: {e}")

    def predict_priority(self, node_id: int, status: str) -> str:
        """Ejecuta la predicción basada en las características ingresadas."""
        if self.model is None:
            return "Pendiente" # Fallback de seguridad si el modelo falla
        
        # Transformamos el texto a código numérico tal como lo entrenamos (0: Normal, 1: Emergencia)
        status_code = 0 if status.lower() == "normal" else 1
        
        # Preparamos el array de entrada (Features)
        X = np.array([[node_id, status_code]])
        
        # Ejecutamos la predicción
        prediction = self.model.predict(X)
        return prediction[0]

# Instanciamos el modelo para que se cargue en memoria una sola vez
triage_model = TriageModel()