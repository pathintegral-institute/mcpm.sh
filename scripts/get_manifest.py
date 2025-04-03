"""Generate MCP server manifests from GitHub repositories."""
import json
import os
import sys
import asyncio
import requests
from typing import Dict, Optional, List, Any

import boto3
from loguru import logger

from scripts.categorization import LLMModel, CategorizationAgent


class ManifestGenerator:
    """Generate and manage MCP server manifests from GitHub repositories."""

    def __init__(self):
        """Initialize with AWS Bedrock client."""
        self.client = boto3.client('bedrock-runtime')
        self.default_repo_url = (
            "https://github.com/modelcontextprotocol/servers/blob/main/src/brave-search"
        )

    def fetch_readme(self, repo_url: str) -> str:
        """Fetch README.md content from a GitHub repository.

        Args:
            repo_url: GitHub repository URL

        Returns:
            README.md content as string

        Raises:
            ValueError: If URL is invalid or README cannot be fetched
        """
        raw_url = self._convert_to_raw_url(repo_url)
        response = requests.get(raw_url)

        if response.status_code != 200 and 'main' in raw_url:
            raw_url = raw_url.replace('/main/', '/master/')
            response = requests.get(raw_url)

        if response.status_code != 200:
            raise ValueError(
                f"Failed to fetch README.md from {repo_url}. "
                f"Status code: {response.status_code}"
            )

        return response.text

    def _convert_to_raw_url(self, repo_url: str) -> str:
        """Convert GitHub URL to raw content URL for README.md."""
        if 'github.com' not in repo_url:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        if '/blob/' in repo_url:
            raw_url = repo_url.replace('/blob/', '/raw/')
            return raw_url if raw_url.endswith('README.md') else f"{raw_url}/README.md"

        raw_url = repo_url.replace('github.com', 'raw.githubusercontent.com')
        return f"{raw_url.rstrip('/')}/main/README.md"

    def extract_repo_info(self, repo_url: str) -> Dict[str, str]:
        """Extract repository owner and name from GitHub URL.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Dictionary containing owner, name, and full URL

        Raises:
            ValueError: If URL format is invalid
        """
        repo_url = repo_url or self.default_repo_url

        parts = repo_url.strip('/').split('/')
        if len(parts) < 5 or parts[2] != 'github.com':
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        owner, repo = parts[3], parts[4]
        return {
            'owner': owner,
            'name': repo,
            'full_url': f"https://github.com/{owner}/{repo}"
        }

    def generate_manifest(self, repo_url: str, server_name: Optional[str] = None) -> Dict:
        """Generate MCP server manifest from GitHub repository.

        Args:
            repo_url: GitHub repository URL (uses default if None)
            server_name: Optional server name (derived from URL if None)

        Returns:
            MCP server manifest dictionary
        """
        # Use default repo URL if none provided
        repo_url = repo_url or self.default_repo_url

        # Extract repo info and fetch README
        repo_info = self.extract_repo_info(repo_url)
        readme_content = self.fetch_readme(repo_url)

        # Generate or use server name
        server_name = server_name or self._format_server_name(
            repo_info['name'])

        # Extract manifest information using LLM
        manifest = self._extract_with_llms(
            self._create_prompt(repo_url, readme_content)
        )

        # Update manifest with repository information
        manifest.update({
            'name': server_name,
            'repository': {'type': 'git', 'url': repo_info['full_url']},
            'author': manifest.get('author') or {'name': repo_info['owner']}
        })

        # Get categories and tags
        server_info = {
            "name": manifest.get("name", ""),
            "description": manifest.get("description", "")
        }

        categorized_servers = asyncio.run(
            self.categorize_servers([server_info]))
        if categorized_servers:
            manifest["categories"] = [
                categorized_servers[0].get("category", "Unknown")]
            manifest["tags"] = []
            logger.info(f"Server categorized as: {manifest['categories'][0]}")

        return manifest

    async def categorize_servers(
        self,
        servers: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Categorize a list of servers.

        Args:
            servers: List of server dictionaries with 'name' and 'description'

        Returns:
            List of dictionaries with categorization results
        """
        agent = CategorizationAgent()
        results = []

        for server in servers:
            result = await agent.execute(
                server_name=server["name"],
                server_description=server["description"],
                include_examples=True
            )
            result["server_name"] = server["name"]
            results.append(result)

        return results

    def _format_server_name(self, repo_name: str) -> str:
        """Convert repository name to kebab-case."""
        name = repo_name.lower()
        name = ''.join('-' if not char.isalnum() else char for char in name)
        return '-'.join(filter(None, name.strip('-').split('--')))

    def _create_prompt(self, repo_url: str, readme_content: str) -> str:
        """Create prompt for manifest information extraction.

        Structures the prompt with static content first for better caching:
        1. System instructions (static)
        2. JSON schema (static)
        3. GitHub URL and README content (variable)

        This approach optimizes prompt caching by placing fixed content at the beginning
        and variable content at the end.
        """
        schema = {
            "name": "string", "display_name": "string", "version": "string",
            "description": "string", "repository": {"type": "git", "url": "string"},
            "homepage": "string", "author": {"name": "string", "email": "string",
                                             "url": "string"},
            "license": "string", "categories": ["string"], "tags": ["string"],
            "arguments": {"string": {"description": "string", "required": bool,
                                     "example": "string"}},
            "installations": {"string": {"type": "string", "command": "string",
                                         "args": ["string"],
                                         "package": "string",
                                         "env": {"string": "string"},
                                         "description": "string",
                                         "recommended": bool}},
            "examples": [{"title": "string", "description": "string",
                          "prompt": "string"}]
        }

        # Static content first for better caching
        static_content = (
            "You are a helpful assistant that analyzes GitHub README.md "
            "files.\n"
            "Extract information from the README and return it in JSON "
            "format.\n"
            "Use [NOT GIVEN] for missing information.\n\n"
            f"JSON Schema: {json.dumps(schema, indent=2)}\n\n"
        )

        # Variable content at the end
        variable_content = (
            f"GitHub URL: {repo_url}\n\n"
            f"README Content:\n{readme_content}\n\n"
            "Format the extracted information as JSON according to the schema."
        )

        return static_content + variable_content

    def _extract_with_llms(self, prompt: str) -> Dict:
        """Extract manifest information using Amazon Bedrock with optimized caching.

        The prompt is structured with static content first (instructions, schema)
        followed by variable content (URL, README), to maximize cache efficiency.
        """
        try:
            # Split prompt to place cache point after static content for better caching
            prompt_parts = prompt.split("GitHub URL:")
            static_part = prompt_parts[0]
            dynamic_part = "GitHub URL:" + \
                prompt_parts[1] if len(prompt_parts) > 1 else ""

            response = self.client.converse(
                modelId=LLMModel.CLAUDE_3_7_SONNET,
                system=[
                    {"text": "You are a helpful assistant for README analysis."}
                ],
                messages=[{
                    "role": "user",
                    "content": [
                        {"text": static_part},
                        {"cachePoint": {"type": "default"}},
                        {"text": dynamic_part}
                    ]
                }],
                inferenceConfig={"temperature": 0.0},
                responseFormat={"type": "json_object"}
            )

            content = response['output']['message']['content']
            return json.loads(next(item['text'] for item in content if 'text' in item))

        except (KeyError, json.JSONDecodeError, StopIteration) as e:
            logger.error(f"Failed to process Bedrock response: {e}")
            raise e
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            raise e


def main(repo_url: str):
    try:
        generator = ManifestGenerator()
        manifest = generator.generate_manifest(repo_url)

        logger.info(json.dumps(manifest, indent=2))

        filename = f"{manifest['name']}.json"
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(manifest, file, indent=2)
        logger.info(f"Manifest saved to {filename}")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Process command-line arguments and generate manifest."""
    if len(sys.argv) < 2:
        logger.info("Usage: python script.py <github-url>")
        sys.exit(1)

    repo_url = sys.argv[1].strip()
    if not repo_url.startswith(('http://', 'https://')):
        logger.error("Error: URL must start with http:// or https://")
        sys.exit(1)

    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    logger.info(f"Processing GitHub URL: {repo_url}")

    main(repo_url)
