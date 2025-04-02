import sys
import requests
import json
import openai


def scrape_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content = response.json()

        # for testing
        with open('scraped_content.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Scraped content from {url}")
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    issue_body = sys.argv[1]
    # Extract URL from issue body (assumes link is on its own line)
    # TODO: need a more robust way to extract the URL
    for line in issue_body.split('\n'):
        line = line.strip()
        if line.startswith('http://') or line.startswith('https://'):
            scrape_url(line)
            break
    else:
        print("No valid URL found in issue body")
        sys.exit(1)
