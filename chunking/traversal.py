from pathlib import Path

IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv',
    'venv', 'dist', 'build', 'vendor', '.next', '.cache'
}

IGNORE_EXTENSIONS = {
    '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin',
    '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
    '.lock', '.sum'
}


MAX_FILE_BYTES = 500_000

def walk_repo(root: str) -> list[dict]:
    records = []
    root_path = Path(root)
    
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
    
        if any(part in IGNORE_DIRS for part in file_path.parts):
            continue
        if file_path.suffix in IGNORE_EXTENSIONS:
            continue
        if file_path.stat().st_size > MAX_FILE_BYTES:
            continue
        
        try:
            raw = file_path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            continue
        
        records.append({
            "path": str(file_path.relative_to(root_path)),
            "language": file_path.suffix.lstrip(".") or "unknown",
            "size": file_path.stat().st_size,
            "lines": raw.count("\n"),
            "raw": raw
        })

    return records



if __name__ == "__main__":
    import sys
    records = walk_repo(sys.argv[1])
    langs = {}
    for r in records:
        langs[r["language"]] = langs.get(r["language"], 0) + 1
        # print(r.get("raw"))
