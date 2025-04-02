import sys
import requests
import os


def is_valid_markdown(content):
    # Basic check for valid Markdown (customize as needed)
    return bool(content.strip()) and content != 'Not Found'


def fetch_readme(url):
    # Convert GitHub blob URL to raw URL and append /README.md
    if 'blob' in url:
        raw_url = url.replace('blob', 'raw') + '/README.md'
    else:
        raw_url = url + '/raw/main/README.md'

    try:
        # Try fetching from the raw URL
        print(f"Fetching README from: {raw_url}")
        response = requests.get(raw_url, timeout=10)
        response.raise_for_status()

        # Check if content is valid Markdown
        if not is_valid_markdown(response.text):
            # Fallback to /master/ if /main/ fails
            raw_url = raw_url.replace('/main/', '/master/')
            print(f"Retrying with: {raw_url}")
            response = requests.get(raw_url, timeout=10)
            response.raise_for_status()

        if not is_valid_markdown(response.text):
            print(
                f"Error: Fetched content from {raw_url} is not valid Markdown")
            sys.exit(1)

        # Ensure the output directory exists
        # Change to desired folder (e.g., 'downloads' or '')
        output_dir = 'local'
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save the README content in the local folder
        output_file = os.path.join(
            output_dir, 'readme.md') if output_dir else 'readme.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved README to {output_file}")

    except requests.RequestException as e:
        print(f"Error fetching README from {raw_url}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No URL provided")
        sys.exit(1)

    url = sys.argv[1].strip()
    # Basic URL validation
    if not (url.startswith('http://') or url.startswith('https://')):
        print("Invalid URL provided")
        sys.exit(1)

    fetch_readme(url)
