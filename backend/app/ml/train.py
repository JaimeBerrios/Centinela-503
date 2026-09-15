import os
import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier

def train_dummy_model():
    print("Preparando datos de entrenamiento sintéticos...")
    # Nuestras características (Features): [node_id, status_code]
    # status_code -> 0: Normal, 1: Emergencia
    X = np.array([
        [1, 0], [2, 1], [1, 0], [2, 1], 
        [1, 1], [2, 0], [1, 1], [2, 0]
    ])
    
    # Nuestras etiquetas (Labels): La prioridad que queremos predecir
    y = np.array(['Baja', 'Alta', 'Baja', 'Alta', 'Alta', 'Baja', 'Alta', 'Baja'])

    print("Entrenando el modelo de Árbol de Decisión...")
    model = DecisionTreeClassifier(random_state=42)
    model.fit(X, y)

    # Aseguramos que la carpeta artifacts exista
    artifacts_dir = os.path.join(os.path.dirname(__file__), 'artifacts')
    os.makedirs(artifacts_dir, exist_ok=True)
    
    # Guardamos el modelo
    model_path = os.path.join(artifacts_dir, 'model.pkl')
    joblib.dump(model, model_path)
    
    print(f"¡Éxito! Modelo entrenado y guardado en: {model_path}")

if __name__ == "__main__":
    train_dummy_model()