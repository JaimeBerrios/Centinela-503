"""SQLite persistence for the offline Centinela pilot."""
from contextlib import contextmanager
import json
import os
import sqlite3
from app.core.config import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "", 1)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


@contextmanager
def connection():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def init_db():
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sensors_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            priority TEXT DEFAULT 'Pendiente',
            incident_text TEXT DEFAULT '',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            category TEXT DEFAULT 'Sin clasificar',
            suggested_priority TEXT DEFAULT 'Pendiente',
            suggested_reason TEXT DEFAULT '',
            triage_state TEXT DEFAULT 'Pendiente de validación',
            resolution_status TEXT DEFAULT 'Abierta',
            source TEXT DEFAULT 'hardware',
            reporter_id INTEGER REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','coordinator','brigade_operator','reporter')),
            brigade_id INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            attempted_at TEXT NOT NULL,
            succeeded INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS brigades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            zone TEXT NOT NULL DEFAULT '',
            skills TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'Disponible',
            latitude REAL,
            longitude REAL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL REFERENCES sensors_data(id),
            brigade_id INTEGER NOT NULL REFERENCES brigades(id),
            assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'Asignada',
            note TEXT NOT NULL DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER REFERENCES sensors_data(id) ON DELETE SET NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS policies (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON sensors_data(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments(status);
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);
        """)

        # Upgrade databases from the initial dashboard without losing records.
        incident_columns = _columns(conn, "sensors_data")
        legacy_priority_only = "triage_state" not in incident_columns
        migrations = {
            "incident_text": "TEXT DEFAULT ''",
            "category": "TEXT DEFAULT 'Sin clasificar'",
            "suggested_priority": "TEXT DEFAULT 'Pendiente'",
            "suggested_reason": "TEXT DEFAULT ''",
            "triage_state": "TEXT DEFAULT 'Pendiente de validación'",
            "resolution_status": "TEXT DEFAULT 'Abierta'",
            "source": "TEXT DEFAULT 'hardware'",
            "reporter_id": "INTEGER REFERENCES users(id) ON DELETE SET NULL",
        }
        for name, definition in migrations.items():
            if name not in incident_columns:
                conn.execute(f"ALTER TABLE sensors_data ADD COLUMN {name} {definition}")
        if legacy_priority_only:
            conn.execute("""UPDATE sensors_data SET suggested_priority=CASE
                         WHEN priority IN ('Alta','Media','Baja') THEN priority ELSE 'Pendiente' END,
                         priority='Pendiente',triage_state='Pendiente de validación'""")
        user_columns = _columns(conn, "users")
        if "brigade_id" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN brigade_id INTEGER")

        defaults = {
            "cluster_radius_m": "50",
            "simulator_enabled": "true",
        }
        for key, value in defaults.items():
            conn.execute("INSERT OR IGNORE INTO policies(key, value) VALUES(?, ?)", (key, value))


def insert_sensor_data(node_id: int, status: str, priority: str = "Pendiente", lat: float = 0.0,
                       lon: float = 0.0, incident_text: str = "", *, category: str = "Sin clasificar",
                       suggested_priority: str = "Pendiente", suggested_reason: str = "",
                       triage_state: str = "Pendiente de validación",
                       source: str = "hardware", reporter_id: int | None = None) -> int:
    with connection() as conn:
        cursor = conn.execute(
            """INSERT INTO sensors_data
               (node_id,status,latitude,longitude,priority,incident_text,category,
                suggested_priority,suggested_reason,triage_state,source,reporter_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (node_id, status, lat, lon, priority, incident_text, category,
             suggested_priority, suggested_reason, triage_state, source, reporter_id),
        )
        return cursor.lastrowid


def get_all_sensors_data(limit: int | None = None):
    with connection() as conn:
        if limit:
            rows = conn.execute("SELECT * FROM sensors_data ORDER BY timestamp DESC,id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sensors_data ORDER BY timestamp DESC,id DESC").fetchall()
        return [dict(row) for row in rows]


def get_incident(incident_id: int):
    with connection() as conn:
        row = conn.execute("SELECT * FROM sensors_data WHERE id=?", (incident_id,)).fetchone()
        return dict(row) if row else None


def update_incident(incident_id: int, fields: dict):
    allowed = {"priority", "triage_state", "resolution_status"}
    fields = {key: value for key, value in fields.items() if key in allowed}
    if not fields:
        return get_incident(incident_id)
    assignments = ", ".join(f"{key}=?" for key in fields)
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        previous = conn.execute("SELECT * FROM sensors_data WHERE id=?", (incident_id,)).fetchone()
        if not previous:
            return None
        if fields.get("triage_state", previous["triage_state"]) == "Validada" and fields.get("priority", previous["priority"]) not in ("Alta", "Media", "Baja"):
            raise ValueError("Define una prioridad Alta, Media o Baja antes de validar.")
        active = conn.execute("SELECT * FROM assignments WHERE incident_id=? AND status IN ('Asignada','En camino','Atendiendo')", (incident_id,)).fetchall()
        resolution = fields.get("resolution_status")
        if resolution in ("Asignada", "En atención", "Abierta") and resolution != previous["resolution_status"]:
            if active or resolution != "Abierta":
                raise ValueError("Actualiza el avance desde la asignación de la brigada.")
        if resolution in ("Resuelta", "Cancelada"):
            assignment_status = "Completada" if resolution == "Resuelta" else "Cancelada"
            conn.execute("UPDATE assignments SET status=?,completed_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE incident_id=? AND status IN ('Asignada','En camino','Atendiendo')", (assignment_status, incident_id))
            for assignment in active:
                conn.execute("""UPDATE brigades SET status='Disponible',updated_at=CURRENT_TIMESTAMP
                    WHERE id=? AND status='Asignada' AND NOT EXISTS (
                        SELECT 1 FROM assignments WHERE brigade_id=brigades.id
                        AND status IN ('Asignada','En camino','Atendiendo'))""", (assignment["brigade_id"],))
        conn.execute(f"UPDATE sensors_data SET {assignments} WHERE id=?", (*fields.values(), incident_id))
        row = conn.execute("SELECT * FROM sensors_data WHERE id=?", (incident_id,)).fetchone()
        return dict(row) if row else None


def create_user(username: str, full_name: str, password_hash: str, role: str, brigade_id=None):
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users(username,full_name,password_hash,role,brigade_id) VALUES(?,?,?,?,?)",
            (username.strip().lower(), full_name.strip(), password_hash, role, brigade_id),
        )
        row = conn.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def get_user(user_id: int):
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str):
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username.strip(),)).fetchone()
        return dict(row) if row else None


def list_users():
    with connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT u.id,u.username,u.full_name,u.role,u.brigade_id,u.active,u.created_at,
                      b.name AS brigade_name FROM users u LEFT JOIN brigades b ON b.id=u.brigade_id
               ORDER BY u.full_name COLLATE NOCASE""").fetchall()]


def count_users():
    with connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def update_user(user_id: int, fields: dict):
    allowed = {"full_name", "role", "brigade_id", "active", "password_hash"}
    fields = {key: value for key, value in fields.items() if key in allowed}
    if not fields:
        return get_user(user_id)
    values = list(fields.values())
    assignments = ", ".join(f"{key}=?" for key in fields)
    with connection() as conn:
        conn.execute(f"UPDATE users SET {assignments} WHERE id=?", (*values, user_id))
        if fields.get("active") in (False, 0) or "password_hash" in fields:
            conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def active_admin_count():
    with connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]


def save_session(token_hash: str, user_id: int, expires_at: str):
    with connection() as conn:
        conn.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (token_hash,user_id,expires_at))


def get_session_user(token_hash: str, now: str):
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        row = conn.execute(
            """SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
               WHERE s.token_hash=? AND s.expires_at>? AND u.active=1""", (token_hash, now)
        ).fetchone()
        return dict(row) if row else None


def delete_session(token_hash: str):
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))


def log_login_attempt(username: str, attempted_at: str, succeeded: bool):
    with connection() as conn:
        conn.execute("INSERT INTO login_attempts(username,attempted_at,succeeded) VALUES(?,?,?)",
                     (username.strip().lower(), attempted_at, int(succeeded)))
        conn.execute("DELETE FROM login_attempts WHERE attempted_at < datetime('now','-1 day')")


def failed_login_count(username: str, since: str):
    with connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM login_attempts WHERE username=? AND succeeded=0 AND attempted_at>=?",
                            (username.strip().lower(), since)).fetchone()[0]


def create_brigade(name: str, zone: str, skills: list[str], latitude=None, longitude=None):
    with connection() as conn:
        cursor = conn.execute("INSERT INTO brigades(name,zone,skills,latitude,longitude) VALUES(?,?,?,?,?)",
                              (name.strip(), zone.strip(), json.dumps(skills, ensure_ascii=False), latitude, longitude))
        row = conn.execute("SELECT * FROM brigades WHERE id=?", (cursor.lastrowid,)).fetchone()
        item = dict(row)
        item["skills"] = json.loads(item["skills"] or "[]")
        return item


def get_brigade(brigade_id: int):
    with connection() as conn:
        row = conn.execute("SELECT * FROM brigades WHERE id=?", (brigade_id,)).fetchone()
        return dict(row) if row else None


def list_brigades():
    with connection() as conn:
        rows = conn.execute("""SELECT b.*, COUNT(DISTINCT CASE WHEN a.status IN ('Asignada','En camino','Atendiendo')
                                  THEN a.id END) AS active_assignments
                           FROM brigades b LEFT JOIN assignments a ON a.brigade_id=b.id
                           GROUP BY b.id ORDER BY b.name COLLATE NOCASE""").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try: item["skills"] = json.loads(item["skills"] or "[]")
            except json.JSONDecodeError: item["skills"] = []
            result.append(item)
        return result


def update_brigade(brigade_id: int, fields: dict):
    allowed = {"name", "zone", "skills", "status", "latitude", "longitude"}
    updates = {key: (json.dumps(value, ensure_ascii=False) if key == "skills" and not isinstance(value, str) else value)
               for key, value in fields.items() if key in allowed}
    if not updates: return get_brigade(brigade_id)
    assignments = ", ".join(f"{key}=?" for key in updates)
    assignments += ", updated_at=CURRENT_TIMESTAMP"
    params = tuple(updates.values())
    with connection() as conn:
        conn.execute(f"UPDATE brigades SET {assignments} WHERE id=?", (*params, brigade_id))
        row = conn.execute("SELECT * FROM brigades WHERE id=?", (brigade_id,)).fetchone()
        if not row: return None
        item = dict(row)
        try: item["skills"] = json.loads(item["skills"] or "[]")
        except json.JSONDecodeError: item["skills"] = []
        return item


def create_assignment(incident_id: int, brigade_id: int, assigned_by: int, note: str):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        incident = conn.execute("SELECT * FROM sensors_data WHERE id=?", (incident_id,)).fetchone()
        if not incident or incident["resolution_status"] in ("Resuelta", "Cancelada"):
            raise ValueError("La alerta no existe o ya está cerrada.")
        if incident["triage_state"] != "Validada" or incident["priority"] not in ("Alta", "Media", "Baja"):
            raise ValueError("Define y valida una prioridad antes de asignar.")
        if conn.execute("SELECT 1 FROM assignments WHERE (incident_id=? OR brigade_id=?) AND status IN ('Asignada','En camino','Atendiendo')", (incident_id, brigade_id)).fetchone():
            raise ValueError("La alerta o la brigada ya tiene una asignación activa.")
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM brigades WHERE id=?", (brigade_id,))
        b_status = cursor.fetchone()
        if not b_status or b_status["status"] != "Disponible":
            raise ValueError("La brigada ya no está disponible.")
        cursor.execute("INSERT INTO assignments(incident_id,brigade_id,assigned_by,note) VALUES(?,?,?,?)",
                       (incident_id,brigade_id,assigned_by,note.strip()))
        inserted_id = cursor.lastrowid
        cursor.execute("UPDATE sensors_data SET resolution_status='Asignada' WHERE id=?", (incident_id,))
        cursor.execute("UPDATE brigades SET status='Asignada',updated_at=CURRENT_TIMESTAMP WHERE id=?", (brigade_id,))
        return inserted_id


def list_assignments():
    with connection() as conn:
        rows = conn.execute("""SELECT a.*, b.name AS brigade_name, b.zone AS brigade_zone,
                                    i.incident_text, i.category, i.priority, i.suggested_priority,
                                    i.latitude, i.longitude, i.status AS incident_type,
                                    u.full_name AS assigned_by_name
                             FROM assignments a JOIN brigades b ON b.id=a.brigade_id
                             JOIN sensors_data i ON i.id=a.incident_id
                             LEFT JOIN users u ON u.id=a.assigned_by
                             ORDER BY a.created_at DESC,a.id DESC""").fetchall()
        return [dict(row) for row in rows]


def get_assignment(assignment_id: int):
    with connection() as conn:
        row = conn.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        return dict(row) if row else None


def update_assignment(assignment_id: int, status: str, details: str):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        if not row: return None
        transitions = {"Asignada": {"En camino", "Atendiendo", "Completada", "Cancelada"},
                       "En camino": {"Atendiendo", "Completada", "Cancelada"},
                       "Atendiendo": {"Completada", "Cancelada"}}
        if status not in transitions.get(row["status"], set()):
            raise ValueError("La asignación ya cambió de estado; actualiza la vista.")
        completed = "CURRENT_TIMESTAMP" if status in ("Completada", "Cancelada") else None
        conn.execute("""UPDATE assignments SET status=?,note=?,updated_at=CURRENT_TIMESTAMP,
                    completed_at=CASE WHEN ? IS NULL THEN completed_at ELSE CURRENT_TIMESTAMP END WHERE id=?""",
                    (status, details.strip() or row["note"], completed, assignment_id))
        if status == "Completada":
            conn.execute("UPDATE sensors_data SET resolution_status='Resuelta' WHERE id=?", (row["incident_id"],))
        elif status == "Atendiendo":
            conn.execute("UPDATE sensors_data SET resolution_status='En atención' WHERE id=?", (row["incident_id"],))
        elif status == "En camino":
            conn.execute("UPDATE sensors_data SET resolution_status='Asignada' WHERE id=?", (row["incident_id"],))
        elif status == "Cancelada":
            conn.execute("UPDATE sensors_data SET resolution_status='Abierta' WHERE id=?", (row["incident_id"],))
        active = conn.execute("SELECT COUNT(*) FROM assignments WHERE brigade_id=? AND status IN ('Asignada','En camino','Atendiendo')",
                              (row["brigade_id"],)).fetchone()[0]
        conn.execute("UPDATE brigades SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     ("Asignada" if active else "Disponible", row["brigade_id"]))
        return dict(conn.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone())


def create_decision(incident_id, user_id, action: str, details: str):
    with connection() as conn:
        cursor = conn.execute("INSERT INTO decisions(incident_id,user_id,action,details) VALUES(?,?,?,?)",
                              (incident_id,user_id,action,details.strip()))
        return cursor.lastrowid


def list_decisions(limit: int = 100):
    with connection() as conn:
        rows = conn.execute("""SELECT d.*,u.full_name AS user_name,i.incident_text
                             FROM decisions d LEFT JOIN users u ON u.id=d.user_id
                             LEFT JOIN sensors_data i ON i.id=d.incident_id
                             ORDER BY d.created_at DESC,d.id DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(row) for row in rows]


def log_audit(user_id, action: str, entity: str, entity_id, details: dict):
    with connection() as conn:
        cursor = conn.execute("INSERT INTO audit_log(user_id,action,entity,entity_id,details) VALUES(?,?,?,?,?)",
                              (user_id,action,entity,entity_id,json.dumps(details,ensure_ascii=False,default=str)))
        return cursor.lastrowid


def list_audit(limit: int = 200):
    with connection() as conn:
        rows = conn.execute("""SELECT a.*,u.username,u.full_name FROM audit_log a
                             LEFT JOIN users u ON u.id=a.user_id
                             ORDER BY a.created_at DESC,a.id DESC LIMIT ?""", (limit,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try: item["details"] = json.loads(item["details"] or "{}")
            except json.JSONDecodeError: item["details"] = {}
            result.append(item)
        return result


def list_policies():
    with connection() as conn:
        return {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM policies")}


def update_policies(values: dict, user_id: int):
    with connection() as conn:
        for key,value in values.items():
            if value is not None:
                conn.execute("""INSERT INTO policies(key,value,updated_by,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP)
                              ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_by=excluded.updated_by,
                              updated_at=CURRENT_TIMESTAMP""",(key,str(value).lower() if isinstance(value,bool) else str(value),user_id))
    return list_policies()


def dashboard_summary():
    with connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM sensors_data").fetchone()[0]
        open_count = conn.execute("SELECT COUNT(*) FROM sensors_data WHERE resolution_status NOT IN ('Resuelta','Cancelada')").fetchone()[0]
        high = conn.execute("SELECT COUNT(*) FROM sensors_data WHERE priority='Alta' AND resolution_status NOT IN ('Resuelta','Cancelada')").fetchone()[0]
        unassigned = conn.execute("""SELECT COUNT(*) FROM sensors_data i WHERE i.resolution_status='Abierta'
                                   AND NOT EXISTS(SELECT 1 FROM assignments a WHERE a.incident_id=i.id AND a.status NOT IN ('Completada','Cancelada'))""").fetchone()[0]
        active_assignments = conn.execute("SELECT COUNT(*) FROM assignments WHERE status IN ('Asignada','En camino','Atendiendo')").fetchone()[0]
        return {"total_incidents": total, "open_incidents": open_count, "high_priority_open": high,
                "unassigned_incidents": unassigned, "active_assignments": active_assignments}


def delete_incidents_bulk(incident_ids: list[int]) -> int:
    import sqlite3
    with connection() as conn:
        cursor = conn.cursor()
        # Verify if any has assignments
        placeholders = ",".join("?" * len(incident_ids))
        cursor.execute(f"SELECT COUNT(*) FROM assignments WHERE incident_id IN ({placeholders})", incident_ids)
        if cursor.fetchone()[0] > 0:
            raise ValueError("No se pueden eliminar alertas que ya tienen brigadas asignadas.")
        cursor.execute(f"DELETE FROM sensors_data WHERE id IN ({placeholders})", incident_ids)
        return cursor.rowcount

def delete_incident(incident_id: int) -> bool:
    import sqlite3
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM assignments WHERE incident_id=?", (incident_id,))
        if cursor.fetchone()[0] > 0:
            raise ValueError("No se puede eliminar porque tiene brigadas asignadas.")
        cursor.execute("DELETE FROM sensors_data WHERE id=?", (incident_id,))
        return cursor.rowcount > 0
