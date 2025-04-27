#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
import requests

# Constants
GITHUB_API_URL = "https://api.github.com/graphql"
BATCH_SIZE = 50  # Process repositories in batches of 50 to avoid rate limits
SCHEMA_PATH = Path("mcp-registry/schema/server-schema.json")


def error_exit(message: str) -> None:
    """Print error message and exit with error code"""
    print(f"❌ {message}")
    sys.exit(1)


def status_message(message: str) -> None:
    """Print status message"""
    print(f"🔄 {message}")


def load_schema() -> Dict[str, Any]:
    """Load the JSON schema for validation"""
    try:
        with open(SCHEMA_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        error_exit(f"Invalid JSON in schema file: {e}")
    except FileNotFoundError:
        error_exit(f"Schema file not found at {SCHEMA_PATH}")
    except Exception as e:
        error_exit(f"Error reading schema file: {e}")


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Load and parse a manifest file with schema validation"""
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        # Get the schema
        schema = load_schema()

        # Validate against schema (will raise exception if invalid)
        try:
            jsonschema.validate(instance=manifest, schema=schema)
        except jsonschema.exceptions.ValidationError:
            # If validation fails, we continue but log a warning
            # This allows the site to build even with some schema issues
            print(f"⚠️ Warning: {manifest_path} does not fully conform to the schema")

        return manifest
    except json.JSONDecodeError as e:
        error_exit(f"Invalid JSON in {manifest_path}: {e}")
    except Exception as e:
        error_exit(f"Error reading manifest file {manifest_path}: {e}")


def find_server_manifests(servers_dir: Path) -> List[Path]:
    """Find all server manifest files in the servers directory"""
    if not servers_dir.exists() or not servers_dir.is_dir():
        error_exit(f"Servers directory not found: {servers_dir}")

    server_files = []
    for file_path in servers_dir.glob("*.json"):
        if file_path.is_file():
            server_files.append(file_path)

    return server_files


def extract_github_repos(server_manifests: List[Path]) -> Dict[str, str]:
    """Extract GitHub repository URLs from server manifests"""
    github_repos = {}

    for manifest_path in server_manifests:
        server_name = manifest_path.stem  # Get filename without extension
        manifest = load_manifest(manifest_path)

        # Check if manifest has GitHub repository URL
        if "repository" in manifest:
            repo_url = manifest["repository"]

            # Handle both string and dictionary repository formats
            if isinstance(repo_url, str) and repo_url.startswith("https://github.com/"):
                github_repos[server_name] = repo_url
            elif (
                isinstance(repo_url, dict)
                and "url" in repo_url
                and isinstance(repo_url["url"], str)
                and repo_url["url"].startswith("https://github.com/")
            ):
                github_repos[server_name] = repo_url["url"]

    return github_repos


def fetch_github_stars_batch(repo_urls: List[str]) -> Dict[str, int]:
    """Fetch GitHub stars for multiple repositories using GraphQL API"""
    # Get GitHub token from environment variable
    github_token = os.environ.get("GITHUB_TOKEN")

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
    }

    # Add authorization if token is provided
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    # Extract owner and repo from URLs
    repos = []
    for url in repo_urls:
        if url.startswith("https://github.com/"):
            parts = url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                repos.append((owner, repo))

    if not repos:
        return {}

    stars = {}

    # Process repositories in batches
    for batch_start in range(0, len(repos), BATCH_SIZE):
        batch = repos[batch_start : batch_start + BATCH_SIZE]

        # Construct GraphQL query
        query_parts = []
        variables = {}

        for i, (owner, repo) in enumerate(batch):
            query_parts.append(
                f"""repo{i}: repository(owner: $owner{i}, name: $repo{i}) {{
                stargazerCount
                url
            }}"""
            )
            variables[f"owner{i}"] = owner
            variables[f"repo{i}"] = repo

        # Join the query parts with proper line length
        variable_defs = ", ".join(f"$owner{i}: String!, $repo{i}: String!" for i in range(len(batch)))
        query_body = " ".join(query_parts)

        query = f"""query ({variable_defs}) {{
            {query_body}
        }}"""

        # Send GraphQL request
        try:
            response = requests.post(GITHUB_API_URL, headers=headers, json={"query": query, "variables": variables})

            # Check for errors
            if response.status_code != 200:
                if response.status_code == 401:
                    print("⚠️ GitHub API authentication failed. Set GITHUB_TOKEN for higher rate limits.")
                elif response.status_code == 403:
                    print("⚠️ GitHub API rate limit exceeded. Set GITHUB_TOKEN for higher rate limits.")
                else:
                    print(f"⚠️ GitHub API request failed: status {response.status_code}")
                continue

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                print(f"⚠️ GraphQL errors: {data['errors']}")
                continue

            # Extract star counts
            for i, (owner, repo) in enumerate(batch):
                repo_key = f"repo{i}"
                if repo_key in data["data"] and data["data"][repo_key]:
                    url = data["data"][repo_key]["url"]
                    star_count = data["data"][repo_key]["stargazerCount"]
                    stars[url] = star_count
                    if url.startswith("https://github.com/"):
                        returned_parts = url.replace("https://github.com/", "").split("/")
                        if len(returned_parts) >= 2:
                            returned_owner, returned_repo = returned_parts[0], returned_parts[1]
                            if owner != returned_owner:
                                print(f"⚠️owner mismatch:: {owner} != {returned_owner}")
                            if repo != returned_repo:
                                print(f"⚠️repo mismatch:: {repo} != {returned_repo}")

        except Exception as e:
            print(f"⚠️ Error fetching GitHub stars for batch: {e}")

    return stars


def get_github_stars(github_repos: Dict[str, str]) -> Dict[str, int]:
    """Fetch GitHub stars for all repositories"""
    if not github_repos:
        return {}

    repo_count = len(github_repos)
    status_message(f"Fetching GitHub stars for {repo_count} repositories...")

    # Convert dict values to list for batch processing
    repo_urls = list(github_repos.values())

    # Fetch stars
    url_to_stars = fetch_github_stars_batch(repo_urls)

    # Map server names to star counts
    server_stars = {}
    for server_name, repo_url in github_repos.items():
        if repo_url in url_to_stars:
            server_stars[server_name] = url_to_stars[repo_url]

    return server_stars


def generate_servers_json(server_manifests: List[Path], output_path: Path) -> Dict[str, Dict[str, Any]]:
    """Generate servers.json file with server metadata"""
    status_message("Generating servers.json...")

    servers_data = {}

    for manifest_path in server_manifests:
        server_name = manifest_path.stem  # Get filename without extension
        manifest = load_manifest(manifest_path)

        # Use the entire manifest as is, preserving all fields
        # Ensure the name field at minimum is present
        if "name" not in manifest:
            manifest["name"] = server_name

        servers_data[server_name] = manifest

    # Write servers.json
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(servers_data, f, indent=2)

    return servers_data


def generate_stars_json(stars: Dict[str, int], output_path: Path) -> None:
    """Generate stars.json file with GitHub star counts"""
    status_message("Generating stars.json...")

    # Write stars.json
    with open(output_path, "w") as f:
        json.dump(stars, f, indent=2)


def main() -> None:
    """Main function to prepare site data"""
    if len(sys.argv) < 3:
        error_exit("Usage: prepare.py <source_dir> <target_dir> [--skip-stars]")

    source_dir = Path(sys.argv[1])
    target_dir = Path(sys.argv[2])
    skip_stars = "--skip-stars" in sys.argv

    # Find server manifests
    servers_dir = source_dir / "servers"
    server_manifests = find_server_manifests(servers_dir)

    if not server_manifests:
        error_exit(f"No server manifests found in {servers_dir}")

    # Generate servers.json
    servers_json_path = target_dir / "api" / "servers.json"
    generate_servers_json(server_manifests, servers_json_path)

    # Extract GitHub repositories
    github_repos = extract_github_repos(server_manifests)

    # Generate stars.json (if not skipped)
    stars_json_path = target_dir / "api" / "stars.json"

    if skip_stars and stars_json_path.exists():
        status_message("Skipping GitHub stars fetch as requested.")
    else:
        # Fetch GitHub stars
        stars = get_github_stars(github_repos)
        generate_stars_json(stars, stars_json_path)

    print("✅ Site preparation completed successfully!")


if __name__ == "__main__":
    main()
