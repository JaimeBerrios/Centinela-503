import sqlite3
import os
from app.core.config import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # AGREGAMOS LATITUD Y LONGITUD
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensors_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            priority TEXT DEFAULT 'Pendiente',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# ACTUALIZAMOS LA FUNCIÓN DE INSERCIÓN
def insert_sensor_data(node_id: int, status: str, priority: str = "Pendiente", lat: float = 0.0, lon: float = 0.0) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensors_data (node_id, status, latitude, longitude, priority) VALUES (?, ?, ?, ?, ?)",
        (node_id, status, lat, lon, priority)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_all_sensors_data():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM sensors_data ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]