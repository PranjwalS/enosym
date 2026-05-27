from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript

PARSEABLE = {"py", "js", "ts", "tsx"}


## fetch the right language for parser
def get_language(lang: str):
    if lang == "py":
        return Language(tree_sitter_python.language())
    elif lang == "js":
        return Language(tree_sitter_javascript.language())
    elif lang in {"ts", "tsx"}:
        return Language(tree_sitter_typescript.language_tsx())
    return None



## node parsing
def parse_file(record: dict):
    lang = record["language"]
    if lang not in PARSEABLE:
        return None
    
    language = get_language(lang)
    if language is None:
        return None
    
    parser = Parser()
    parser.language = language
    
    tree = parser.parse(bytes(record["raw"], "utf-8"))
    return tree



if __name__ == "__main__":
    from traversal import walk_repo
    import sys
    
    records = walk_repo(sys.argv[1])
    for record in records:
        tree = parse_file(record)
        # if tree:
        #     print(f"parsed {record['path']} — root node type: {tree.root_node.type}")
        # else:
        #     print(f"skipped {record['path']}")