from app.ml.inference import triage_model

def evaluate_sensor_data(node_id: int, status: str) -> str:
    """
    Evalúa los datos del sensor y determina la prioridad de la alerta
    utilizando el modelo de Machine Learning de Scikit-learn.
    """
    return triage_model.predict_priority(node_id, status)