from collections import Counter
import re
from ranker import cosine_similarity
import difflib

def correct_query(query_tokens, vocab):
    corrected = []

    for word in query_tokens:
        if word in vocab:
            corrected.append(word)
        else:
            matches = difflib.get_close_matches(word, vocab, n=1, cutoff=0.7)
            if matches:
                corrected.append(matches[0])
            else:
                corrected.append(word)

    return corrected

def preprocess_query(query):
    query = query.lower()
    query = re.sub(r'[^a-z0-9\s]', '', query)
    return query.split()


def build_query_vector(query_tokens):
    return Counter(query_tokens)


def search(query, index, tfidf, processed_docs, vocab):
    query_tokens = preprocess_query(query)
    query_tokens = correct_query(query_tokens, vocab)
    query_vec = build_query_vector(query_tokens)

    scores = {}

    for doc_id, doc_vec in tfidf.items():
        match_count = sum(1 for word in query_tokens if word in doc_vec)
        score = cosine_similarity(query_vec, doc_vec) * (1 + match_count)
        if score > 0:
            scores[doc_id] = score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    corrected_query = " ".join(query_tokens)

    return ranked[:10], corrected_query