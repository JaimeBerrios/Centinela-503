import sqlite3
import os
from app.core.config import settings

# Limpiamos el prefijo para la librería nativa sqlite3
DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")

def get_db_connection():
    """Crea y retorna una conexión a SQLite."""
    conn = sqlite3.connect(DB_PATH)
    # Esto permite acceder a las columnas por nombre en lugar de índices numéricos
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    # Aseguramos que la carpeta data/ exista
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla principal para las lecturas del ESP32
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensors_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            priority TEXT DEFAULT 'Pendiente',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Funciones de abstracción (Tus endpoints llamarán a estas)
def insert_sensor_data(node_id: int, status: str, priority: str = "Pendiente") -> int:
    """Inserta una lectura y retorna el ID generado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensors_data (node_id, status, priority) VALUES (?, ?, ?)",
        (node_id, status, priority)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_all_sensors_data():
    """Retorna todas las lecturas ordenadas por fecha."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM sensors_data ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]