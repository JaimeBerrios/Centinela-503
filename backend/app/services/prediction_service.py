import unicodedata
from app.ml.inference import triage_model

def evaluate_sensor_data(node_id: int, status: str) -> str:
    """
    Evalúa los datos del sensor y determina la prioridad de la alerta
    utilizando el modelo de Machine Learning de Scikit-learn.
    """
    return triage_model.predict_priority(node_id, status)


def suggest_triage(text: str, status: str) -> dict:
    """Transparent Spanish keyword baseline; a coordinator must confirm every suggestion."""
    normalized = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")
    categories = {
        "Rescate y lesiones": ("atrapad", "herid", "lesion", "inconsciente", "rescate", "persona bajo"),
        "Inundación": ("inund", "desbord", "crecida", "anegad", "agua subio"),
        "Sismo": ("sismo", "temblor", "terremoto", "movimiento sism"),
        "Incendio": ("incendio", "fuego", "humo", "explosion"),
        "Daño estructural": ("derrumbe", "colaps", "grieta", "pared caida", "techo caido"),
        "Vía obstruida": ("arbol caido", "carretera bloqueada", "via bloqueada", "obstruccion"),
    }
    category = next((name for name, terms in categories.items() if any(term in normalized for term in terms)), "Sin clasificar")
    if status.strip().lower() == "normal":
        return {"category": category, "suggested_priority": "Baja", "basis": "Reporte informativo; validar en coordinación."}
    high_terms = ("atrapad", "herid", "lesion", "inconsciente", "rescate", "incendio", "fuego", "colaps", "derrumbe", "explosion", "desbord", "inundacion")
    medium_terms = ("grieta", "humo", "obstruccion", "arbol caido", "temblor", "sismo", "agua")
    if any(term in normalized for term in high_terms):
        priority, basis = "Alta", "Coincidencia con término de riesgo alto; requiere confirmación humana."
    elif any(term in normalized for term in medium_terms):
        priority, basis = "Media", "Coincidencia con término de riesgo; requiere confirmación humana."
    else:
        priority, basis = "Pendiente", "El texto no coincide con una regla local; requiere clasificación humana."
    return {"category": category, "suggested_priority": priority, "basis": basis}
