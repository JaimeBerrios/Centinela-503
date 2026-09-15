import math

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia en metros entre dos coordenadas GPS usando Haversine."""
    R = 6371000  # Radio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def group_alerts(alerts: list, distance_threshold: float = 50.0) -> list:
    """
    Agrupa las alertas que están a menos de X metros de distancia entre sí.
    Retorna una lista de clústeres.
    """
    clusters = []
    
    for alert in alerts:
        placed = False
        for cluster in clusters:
            # Comparamos contra el centroide (el primer elemento) del clúster
            center = cluster["alerts"][0]
            dist = calculate_distance(
                alert["latitude"], alert["longitude"],
                center["latitude"], center["longitude"]
            )
            
            if dist <= distance_threshold:
                cluster["alerts"].append(alert)
                # Si hay al menos una emergencia en el clúster, todo el clúster sube de prioridad
                if alert["priority"] == "Alta":
                    cluster["cluster_priority"] = "Alta"
                placed = True
                break
                
        if not placed:
            # Crear un nuevo clúster si no encaja en ninguno existente
            clusters.append({
                "cluster_id": len(clusters) + 1,
                "center_latitude": alert["latitude"],
                "center_longitude": alert["longitude"],
                "cluster_priority": alert["priority"],
                "alerts": [alert]
            })
            
    return clusters