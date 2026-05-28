import sqlite3
DB_PATH = "enosym.db"


def get_conn():
    conn = sqlite3.connect("enosym.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()    
    conn.executescript("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id       TEXT PRIMARY KEY,
                    kind     TEXT,
                    name     TEXT,
                    file     TEXT,
                    language TEXT,
                    start_ln INTEGER,
                    end_ln   INTEGER
                );

                CREATE TABLE IF NOT EXISTS edges (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT REFERENCES nodes(id),
                    target TEXT REFERENCES nodes(id),
                    kind   TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_file   ON nodes(file);
                CREATE INDEX IF NOT EXISTS idx_nodes_name   ON nodes(name);
                CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
                CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
                """)  
    conn.commit()
    conn.close()


def save_nodes(node_index):
    conn = get_conn()
    conn.executemany("""
                 INSERT OR REPLACE INTO nodes (id, kind, name, file, language, start_ln, end_ln) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 [(n["id"], n["kind"], n["name"], n["file"], n["language"], n["start"], n["end"]) for key in node_index.keys() for n in [node_index[key]]]
                )
    conn.commit()
    conn.close()
    
def save_edges(edges):
    conn = get_conn()
    conn.executemany("""
                     INSERT OR REPLACE INTO edges (source, target, kind)
                     VALUES (?, ?, ?)""",
                     [(e["source"], e["target"], e["kind"]) for e in edges]
                    )
    conn.commit()
    conn.close()



def get_calls_made_by(node_id:str):
    conn = get_conn()
    rows = conn.execute("""
                        SELECT n.id, n.name, n.file FROM edges e
                        JOIN nodes n ON n.id = e.target
                        WHERE e.source = ?
                        """, (node_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_callers_of(node_id: str):
    conn = get_conn()
    rows = conn.execute("""
                        SELECT n.id, n.name, n.file, n.source FROM edges e
                        JOIN nodes n ON n.id = e.source
                        WHERE e.target = ?
                        """, (node_id, )).fetchall()
    conn.close()
    return [dict(r) for r in rows]
