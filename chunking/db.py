import sqlite3
DB_PATH = "enosym.db"


def get_conn():
    conn = sqlite3.connect("enosym.db")
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


def save_nodes(nodes):
    conn = get_conn()
    conn.executemany("""
                 INSERT INTO nodes (id, kind, name, file, language, start_ln, end_ln) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 [(n["kind"]) for n in nodes])



if __name__ == "__main__":
    init_db()
    print("db initialized")