FUNCTION_TYPES = {
    "py":  ["function_definition", "class_definition"],
    "js":  ["function_declaration", "class_declaration", "arrow_function"],
    "ts":  ["function_declaration", "class_declaration", "arrow_function"],
    "tsx": ["function_declaration", "class_declaration", "arrow_function"],
}

CALL_TYPES = {
    "py":  "call",
    "js":  "call_expression",
    "ts":  "call_expression",
    "tsx": "call_expression",
}

IMPORT_TYPES = {
    "py":  ["import_statement", "import_from_statement"],
    "js":  ["import_statement"],
    "ts":  ["import_statement"],
    "tsx": ["import_statement"],
}



def walk(node, lang, file_path, source):
    nodes = []
    edges = []
    return {"nodes": nodes, "edges": edges}

