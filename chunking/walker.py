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





def walk(node, lang, file_path, source, nodes, edges, parent_id=None):
    func_types = FUNCTION_TYPES.get(lang, [])
    call_type = CALL_TYPES.get(lang)
    import_types = IMPORT_TYPES.get(lang, [])
    
    if node.type in func_types:
        name = _get_name(node, source)
        node_id = f"{file_path}::{name}"
        nodes.append({
            "id":       node_id,
            "kind":     node.type,
            "name":     name,
            "file":     file_path,
            "language": lang,
            "source":   source[node.start_byte:node.end_byte].decode("utf-8"),
            "start":    node.start_point[0],
            "end":      node.end_point[0],
        })
        parent_id = node_id

    for child in node.children:
        walk(child, lang, file_path, source, nodes, edges, parent_id)
    
    
def _get_name(node, source):
    for child in node.children:
        if child.type == "identifier":
            return source[child.start_byte:child.end_byte].decode("utf-8")
    return "anonymous"
 
 
 
 
   
if __name__ == "__main__":
    from traversal import walk_repo
    from parser import parse_file
    import sys
    nodes = []
    edges = []

    records = walk_repo(sys.argv[1])
    for record in records:
        tree = parse_file(record)
        if not tree:
            continue

        walk(tree.root_node, record["language"], record["path"], bytes(record["raw"], "utf-8"), nodes, edges)        
        print(f"\n{record['path']}")
    
    print(f"\ntotal nodes: {len(nodes)}")
    for n in nodes:
        print(f"  {n['id']}")
