import math
from collections import Counter

def compute_tfidf(processed_docs):
    tfidf = {}
    doc_count = len(processed_docs)

    # Document Frequency
    df = {}
    for tokens in processed_docs.values():
        for word in set(tokens):
            df[word] = df.get(word, 0) + 1

    for doc_id, tokens in processed_docs.items():
        tfidf[doc_id] = {}
        tf = Counter(tokens)

        for word, count in tf.items():
            tf_value = count / len(tokens)
            idf_value = math.log((doc_count + 1) / (df[word] + 1)) + 1

            tfidf[doc_id][word] = tf_value * idf_value

    return tfidf


def cosine_similarity(vec1, vec2):
    dot_product = 0
    for word in vec1:
        dot_product += vec1[word] * vec2.get(word, 0)

    norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v**2 for v in vec2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0

    return dot_product / (norm1 * norm2)