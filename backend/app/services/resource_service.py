import unicodedata
from app.services.spatial_service import calculate_distance

REQUIRED_SKILLS = {
    "Rescate y lesiones": ("rescate", "primeros auxilios", "medicina", "paramedico", "ambulancia"),
    "Inundación": ("rescate", "inundacion", "agua", "búsqueda"),
    "Sismo": ("rescate", "estructuras", "ingenieria", "medicina"),
    "Incendio": ("incendio", "bombero", "extintor"),
    "Daño estructural": ("estructuras", "ingenieria", "rescate"),
    "Vía obstruida": ("vial", "mantenimiento", "herramientas"),
}


def _normal(value):
    return "".join(c for c in unicodedata.normalize("NFD", str(value).lower()) if unicodedata.category(c) != "Mn")


def suggest_brigades(incident: dict, brigades: list[dict]) -> list[dict]:
    required = tuple(_normal(skill) for skill in REQUIRED_SKILLS.get(incident.get("category"), ()))
    suggestions = []
    for brigade in brigades:
        if brigade.get("status") != "Disponible": continue
        capabilities = [_normal(skill) for skill in (brigade.get("skills") or [])]
        matched = [skill for skill in required if any(skill in capability or capability in skill for capability in capabilities)]
        distance = None
        try:
            if incident.get("latitude") is not None and incident.get("longitude") is not None and brigade.get("latitude") is not None and brigade.get("longitude") is not None:
                distance = round(calculate_distance(float(incident["latitude"]),float(incident["longitude"]),
                                                    float(brigade["latitude"]),float(brigade["longitude"])) / 1000, 2)
        except (TypeError, ValueError):
            distance = None
        suggestions.append({"brigade_id": brigade["id"], "name": brigade["name"], "zone": brigade.get("zone"),
                            "distance_km_straight_line": distance, "matched_skills": matched,
                            "score": len(matched) * 100 - (distance or 999)})
    return sorted(suggestions, key=lambda item: item["score"], reverse=True)
