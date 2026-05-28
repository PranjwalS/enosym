from embedder import embed, collection
from db import get_calls_made_by, get_callers_of


def search(query: str, k = 5):
    input_embedded = embed(query)
    results = collection.query(
        query_embeddings=[input_embedded],
        n_results = k
    )
    return results


def graph_augmented_search(query: str, k: int = 5):
    results = search(query, k)
    
    expanded_docs = list(results["documents"][0])
    
    for metadata in results["metadatas"][0]:
        node_id = f"{metadata['file']}::{metadata['name']}"
        callees = get_calls_made_by(node_id)
        for callee in callees:
            callee_id = f"{callee['file']}::{callee['name']}"
            fetched = collection.get(ids=[callee_id])
            if fetched["documents"]:
                expanded_docs.append(fetched["documents"][0])
    
    return expanded_docs


if __name__ == "__main__":
    query = input("search: ")
    results = graph_augmented_search(query, 3)
    for doc in results:
        print(doc)
        print("---")