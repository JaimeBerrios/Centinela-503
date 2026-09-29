from datetime import datetime
import math


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia Haversine en metros."""
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dlambda = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1-a)))


def _timestamp(alert):
    value = alert.get("timestamp")
    if not value: return None
    try: return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError: return None


def _valid_point(alert):
    try:
        lat, lon = float(alert.get("latitude")), float(alert.get("longitude"))
        return -90 <= lat <= 90 and -180 <= lon <= 180 and (lat != 0 or lon != 0)
    except (TypeError, ValueError):
        return False


def group_alerts(alerts: list, distance_threshold: float = 50.0, time_window_minutes: int = 15) -> list:
    """Agrupa reportes conectados por distancia y proximidad temporal."""
    count = len(alerts)
    parent = list(range(count))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root: parent[right_root] = left_root

    valid = [index for index, alert in enumerate(alerts) if _valid_point(alert)]
    stamps = [_timestamp(alert) for alert in alerts]
    for offset, left in enumerate(valid):
        a = alerts[left]
        for right in valid[offset+1:]:
            b = alerts[right]
            ta, tb = stamps[left], stamps[right]
            if ta and tb:
                if ta.tzinfo is None and tb.tzinfo is not None: ta = ta.replace(tzinfo=tb.tzinfo)
                if tb.tzinfo is None and ta.tzinfo is not None: tb = tb.replace(tzinfo=ta.tzinfo)
                if abs((ta-tb).total_seconds()) > time_window_minutes*60: continue
            elif ta or tb:
                continue
            if calculate_distance(float(a["latitude"]),float(a["longitude"]),
                                  float(b["latitude"]),float(b["longitude"])) <= distance_threshold:
                union(left,right)

    members = {}
    for index in range(count): members.setdefault(find(index), []).append(alerts[index])
    clusters = []
    for cluster_id, records in enumerate(members.values(), start=1):
        located = [r for r in records if _valid_point(r)]
        if located:
            center_lat = sum(float(r["latitude"]) for r in located) / len(located)
            center_lon = sum(float(r["longitude"]) for r in located) / len(located)
        else:
            center_lat = center_lon = None
        confirmed = [r.get("priority") for r in records if r.get("triage_state") == "Validada"]
        priorities = confirmed or [r.get("suggested_priority") or r.get("priority") for r in records]
        rank = {"Alta":3,"Media":2,"Baja":1}
        cluster_priority = max((p for p in priorities if p in rank), key=lambda p: rank[p], default="Pendiente")
        clusters.append({
            "cluster_id": cluster_id,
            "center_latitude": center_lat,
            "center_longitude": center_lon,
            "cluster_priority": cluster_priority,
            "incident_count": len(records),
            "alerts": records,
        })
    return clusters
