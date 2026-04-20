from crawler import crawl
from preprocess import preprocess
from indexer import build_index
from ranker import compute_tfidf
from search import search
import re


# ✅ Smart snippet extraction
def get_snippet(content, query_words):
    content_lower = content.lower()

    for word in query_words:
        idx = content_lower.find(word)
        if idx != -1:
            start = max(0, idx - 60)
            end = idx + 160
            return content[start:end]

    return content[:200]


# ✅ Highlight query words
def highlight(text, query_words):
    for word in query_words:
        text = re.sub(rf"\b{word}\b", f"**{word}**", text, flags=re.IGNORECASE)
    return text


def main():
    seed_urls = [
    "https://en.wikipedia.org/wiki/Search_engine",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Computer_network",
    "https://en.wikipedia.org/wiki/Data_structure",
    "https://en.wikipedia.org/wiki/Operating_system",
    "https://en.wikipedia.org/wiki/Machine_learning",
    "https://en.wikipedia.org/wiki/Internet",
    "https://iana.org/domains"
]

    print("Starting crawl...")
    documents = crawl(seed_urls, max_pages=30)

    print("Preprocessing...")
    processed_docs = preprocess(documents)

    print("Building index...")
    index = build_index(processed_docs)

    print("Computing TF-IDF...")
    tfidf = compute_tfidf(processed_docs)

    print("\nSearch Engine Ready!\n")

    while True:
        query = input("Enter search query (or 'exit'): ")

        if query.lower() == "exit":
            break

        results = search(query, index, tfidf, processed_docs)

        print("\nTop Results:")

        query_words = query.lower().split()

        for url, score in results:
            data = documents[url]
            content = data["text"]
            title = data["title"]

            snippet = get_snippet(content, query_words)
            snippet = highlight(snippet, query_words)

            print(f"\nTitle: {title}")
            print(f"URL: {url}")
            print(f"Score: {score:.4f}")
            print(f"Snippet: {snippet}...")

        print()


if __name__ == "__main__":
    main()