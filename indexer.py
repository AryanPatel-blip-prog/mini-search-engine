from collections import defaultdict

def build_index(processed_docs):
    index = defaultdict(set)

    for doc_id, tokens in processed_docs.items():
        for token in tokens:
            index[token].add(doc_id)

    return index