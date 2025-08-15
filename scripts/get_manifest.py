#!/usr/bin/env python3
"""
Script to generate MCP manifest JSON from a repository URL.
Uses the chatxiv.org API to generate the manifest and saves it to mcp-registry/servers.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests


def extract_json_from_content(content: str) -> Optional[dict]:
    """Extract JSON from the API response content."""
    # Look for JSON code block
    json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return None
    
    # Try to find JSON without code block markers
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"Could not extract valid JSON from response: {content}")
        return None


def get_repo_name_from_url(repo_url: str) -> str:
    """Extract repository name from URL for filename."""
    # Remove .git suffix if present
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    
    # Extract owner/repo from URL
    match = re.search(r'github\.com[:/]([^/]+/[^/]+)', repo_url)
    if match:
        return match.group(1).replace('/', '-')
    
    # Fallback to last part of URL
    return repo_url.split('/')[-1]


def generate_manifest(repo_url: str) -> Optional[dict]:
    """Generate manifest JSON using the API."""
    api_key = os.getenv("ANYON_API_KEY")
    if not api_key:
        print("Error: ANYON_API_KEY environment variable not set")
        return None
    
    url = "https://anyon.chatxiv.org/api/v1/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "x",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"help me generate manifest json for this repo: {repo_url}"
                    }
                ]
            }
        ]
    }
    
    try:
        print(f"Generating manifest for {repo_url}...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        return extract_json_from_content(content)
        
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Unexpected API response format: {e}")
        return None


def validate_installations(manifest: dict, repo_url: str) -> Optional[dict]:
    """Validate and correct the installations field by having API check the original README."""
    if not manifest:
        return manifest
    
    api_key = os.getenv("ANYON_API_KEY")
    if not api_key:
        print("Error: ANYON_API_KEY environment variable not set, skipping validation")
        return manifest
    
    url = "https://anyon.chatxiv.org/api/v1/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    current_installations = manifest.get("installations", {})
    
    payload = {
        "model": "x",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Please carefully validate and correct the installations field in this manifest by checking the original README.md from the repository.

Repository: {repo_url}

Current manifest installations:
{json.dumps(current_installations, indent=2)}

IMPORTANT INSTRUCTIONS:
1. Access the README.md from the repository URL: {repo_url}
2. Compare the current installations against the exact commands and configurations shown in the README.md
3. Ensure the command, args, and env variables exactly match what's documented in the README. Remove the installation methods which are not mentioned in README.
4. Pay special attention to:
   - Exact command names (npx, uvx, docker, python, etc.)
   - Correct package names and arguments (e.g., for npx command, it should usually be "-y [package_name]"
   - Proper environment variable names and formats
   - Installation type matching the command used
5. Fix any discrepancies between the manifest and the README
6. Return ONLY a valid JSON object with the corrected installations field
7. The response should be in this exact format: {{"installations": {{...}}}}

Focus on accuracy - the installations must work exactly as documented in the README. If the README shows different installation methods, include all valid ones."""
                    }
                ]
            }
        ]
    }
    
    try:
        print("Validating installations against README...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        validated_data = extract_json_from_content(content)
        if validated_data and "installations" in validated_data:
            print("✓ Installations validated and corrected")
            manifest["installations"] = validated_data["installations"]
            return manifest
        else:
            print("⚠ Validation failed, keeping original installations")
            return manifest
            
    except Exception as e:
        print(f"Error validating installations: {e}")
        return manifest


def save_manifest(manifest: dict, repo_url: str) -> bool:
    """Save manifest JSON to mcp-registry/servers directory."""
    # Create directory if it doesn't exist
    servers_dir = Path("mcp-registry/servers")
    servers_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename from repo URL
    repo_name = get_repo_name_from_url(repo_url)
    filename = f"{repo_name}.json"
    filepath = servers_dir / filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"Manifest saved to {filepath}")
        return True
        
    except IOError as e:
        print(f"Failed to save manifest: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate MCP manifest JSON from repository URL")
    parser.add_argument("repo_url", help="Repository URL to generate manifest for")
    
    args = parser.parse_args()
    
    # Step 1: Generate initial manifest
    print("Step 1: Generating initial manifest...")
    manifest = generate_manifest(args.repo_url)
    if not manifest:
        print("Failed to generate manifest")
        sys.exit(1)
    
    # Step 2: Validate and correct installations
    print("Step 2: Validating installations against README...")
    manifest = validate_installations(manifest, args.repo_url)
    
    # Step 3: Save manifest
    print("Step 3: Saving manifest...")
    if not save_manifest(manifest, args.repo_url):
        print("Failed to save manifest")
        sys.exit(1)
    
    print("✓ Manifest generation completed successfully!")


if __name__ == "__main__":
    main()
