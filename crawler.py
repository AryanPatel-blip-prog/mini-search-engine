import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

def crawl(seed_urls, max_pages=20):
    visited = set()
    to_visit = list(seed_urls)
    documents = {}

    headers = {"User-Agent": "Mozilla/5.0"}

    # Extract base domain from seed URL
    base_domain = urlparse(seed_urls[0]).netloc

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)

        if url in visited:
            continue

        try:
            print(f"Crawling: {url}")
            response = requests.get(url, headers=headers, timeout=5)
            html = response.text
        except:
            continue

        visited.add(url)

        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.extract()

        # ✅ Extract title
        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"

        # ✅ Extract meaningful text
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs)

        # fallback if empty
        if not text.strip():
            text = soup.get_text(separator=' ', strip=True)

        # ✅ Store structured data
        documents[url] = {
            "text": text,
            "title": title
        }

        # ✅ Extract links (domain restricted)
        for link in soup.find_all("a", href=True):
            new_url = urljoin(url, link['href'])
            parsed = urlparse(new_url)

            if any(x in new_url for x in [
                "Special:", 
                "Wikipedia:", 
                "Help:", 
                "Talk:", 
                "Portal:",
                "File:",
                "Category:",
                "index.php",
                "action="
            ]):
                continue

            if "#" in new_url or "Main_Page" in new_url:
                continue

            if parsed.netloc == base_domain and new_url not in visited:
                to_visit.append(new_url)

        time.sleep(1)  # politeness delay

    return documents