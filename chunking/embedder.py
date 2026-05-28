import chromadb
from transformers import AutoTokenizer, AutoModel
import torch


MODEL_NAME = "microsoft/unixcoder-base"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

client = chromadb.PersistentClient(path="./chromadb")
collection = client.get_or_create_collection("nodes")


def embed(text: str):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().tolist()

def embed_nodes(node_index):
    for key, node in node_index.items():
        collection.add(
            ids = key,
            embeddings = embed(node["source"]),
            documents = node["source"],
            metadatas={"id": key, "file": node["file"], "name": node["name"], "language": node["language"]}
        )
        
        
if __name__ == "__main__":
    from traversal import walk_repo
    from parser import parse_file
    from walker import walk
    from db import save_edges, save_nodes, init_db
    
    import sys
    
    init_db()
    nodes = []
    edges = []
    
    records = walk_repo(sys.argv[1])
    
    for record in records:
        tree = parse_file(record)
        if not tree:
            continue
        walk(tree.root_node, record["language"], record["path"], bytes(record["raw"], "utf-8"), nodes, edges)
        
    node_index = {n["id"]: n for n in nodes}
    
    for record in records:
        tree = parse_file(record)
        if not tree:
            continue
        walk(tree.root_node, record["language"], record["path"], bytes(record["raw"], "utf-8"), nodes, edges, node_index)
        
    save_nodes(node_index)
    save_edges(edges)
    print(f"indexed {len(node_index)} nodes, {len(edges)} edges")

    embed_nodes(node_index)
    print("embeddings stored")