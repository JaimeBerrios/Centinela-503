from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.api.dependencies import current_user
from app.db import database

router = APIRouter()


@router.get("/overview")
def overview(user=Depends(current_user)):
    all_alerts = database.get_all_sensors_data()
    alerts_for_user = [item for item in all_alerts if user["role"] != "reporter" or item.get("reporter_id") == user["id"]]
    alerts = alerts_for_user[:8]
    brigades = database.list_brigades() if user["role"] != "reporter" else []
    assignments = database.list_assignments() if user["role"] in ("admin", "coordinator", "brigade_operator") else []
    if user["role"] == "brigade_operator":
        assignments = [item for item in assignments if item["brigade_id"] == user.get("brigade_id")]
    decisions = database.list_decisions(8) if user["role"] in ("admin", "coordinator") else []
    policies = database.list_policies() if user["role"] == "admin" else {}
    if user["role"] == "reporter":
        summary = {"total_incidents": len(alerts_for_user),
                   "open_incidents": sum(i.get("resolution_status") not in ("Resuelta", "Cancelada") for i in alerts_for_user),
                   "high_priority_open": 0, "unassigned_incidents": 0, "active_assignments": 0}
    else:
        summary = database.dashboard_summary()
    latest_by_node = {}
    for item in (all_alerts if user["role"] != "reporter" else []):
        node_id = item.get("node_id")
        if node_id and node_id not in latest_by_node:
            latest_by_node[node_id] = item
    now = datetime.now(timezone.utc)
    nodes = []
    for node_id in (1, 2):
        latest = latest_by_node.get(node_id)
        stamp = latest.get("timestamp") if latest else None
        try:
            dt = datetime.fromisoformat(stamp.replace("Z", "+00:00")) if stamp else None
            if dt and dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            online = bool(dt and (now-dt).total_seconds() < 120)
        except (ValueError, TypeError): online = False
        nodes.append({"node_id": node_id, "last_report": stamp, "state": "Reporte reciente" if online else "Sin reporte reciente",
                      "source": latest.get("source") if latest else None})
    return {"summary": summary, "incidents": alerts, "brigades": brigades, "assignments": assignments,
            "decisions": decisions, "nodes": nodes, "policies": policies,
            "user": {"id": user["id"], "role": user["role"], "full_name": user["full_name"]}}
