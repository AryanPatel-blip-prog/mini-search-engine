import re

STOPWORDS = set([
    "the", "is", "and", "in", "to", "of", "a", "on", "for", "with", "as", "by", "an"
])

def preprocess(documents):
    processed = {}

    for doc_id, data in documents.items():
        text = data["text"]
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)

        tokens = text.split()
        tokens = [word for word in tokens if word not in STOPWORDS]

        processed[doc_id] = tokens

    return processed