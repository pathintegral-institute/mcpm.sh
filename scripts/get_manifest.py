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

    def _extract_server_info_from_url(self, repo_url: str) -> Dict[str, str]:
        """Extract server information directly from GitHub URL.

        For URLs from the modelcontextprotocol/servers repo, extracts 
        server name from path. For other repos, extracts from repo name.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Dictionary with 'name', 'url', and placeholder for 'desc'
        """
        # Parse URL to extract components
        parts = repo_url.strip('/').split('/')

        if len(parts) < 5 or parts[2] != 'github.com':
            logger.warning(f"Not a valid GitHub URL: {repo_url}")
            return {
                "name": "",
                "url": repo_url,
                "desc": ""
            }

        # Handle official MCP servers repo URLs which have a specific pattern
        if parts[3] == 'modelcontextprotocol' and parts[4] == 'servers':
            # Find the 'src' directory index
            # Usually it comes after 'blob/main' or 'blob/master'
            src_index = -1
            for i, part in enumerate(parts):
                if part == 'src':
                    src_index = i
                    break

            # Check if we found a server name
            if src_index > 0 and src_index + 1 < len(parts):
                # Get name from path like src/brave-search
                server_name = parts[src_index + 1]

                # This is our trusted source
                url = repo_url

                return {
                    "name": server_name,
                    "url": url,
                    "desc": ""  # Will be extracted from README
                }
            else:
                # Fallback to repo name if structure is unexpected
                server_name = parts[4]  # 'servers'
                logger.warning(
                    f"Could not find server name in URL: {repo_url}")
        else:
            # Third-party repo: use repo name as server name
            server_name = parts[4]

        # Format server name to kebab-case
        server_name = self._format_server_name(server_name)

        return {
            "name": server_name,
            "url": f"https://github.com/{parts[3]}/{parts[4]}",
            "desc": ""  # Will be extracted from README
        }

    def _extract_description_from_readme(self, readme_content: str) -> str:
        """Extract a concise description from README content.

        Looks for the first meaningful description paragraph near the beginning
        of the README, typically after the title.

        Args:
            readme_content: Contents of README.md

        Returns:
            Extracted description or empty string if not found
        """
        try:
            # Split readme into lines
            lines = readme_content.split('\n')

            # Skip empty lines and headers
            description = ""
            in_code_block = False
            for line in lines:
                # Skip code blocks
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue

                # Skip headers, badges and links at the beginning
                if line.strip().startswith('#') or '![' in line or line.strip() == '':
                    continue

                # Found a potential description line
                if len(line.strip()) > 20:  # Reasonable length for description
                    description = line.strip()
                    break

            # If we couldn't find a good description, try to use the project title
            if not description:
                for line in lines:
                    if line.strip().startswith('# '):
                        # Remove the heading marker and return the title
                        title = line.strip()[2:]
                        if len(title) > 3:  # Make sure it's not just a symbol
                            return title

            return description

        except Exception as e:
            logger.error(f"Error extracting description from README: {e}")
            return ""

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
        parts = repo_url.strip('/').split('/')
        if len(parts) < 5 or parts[2] != 'github.com':
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        owner, repo = parts[3], parts[4]
        return {
            'owner': owner,
            'name': repo,
            'full_url': f"https://github.com/{owner}/{repo}"
        }

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

    def _create_prompt(self, repo_url: str, readme_content: str) -> tuple[str, str]:
        """Create prompt for manifest information extraction, returning static and variable parts.

        Returns:
            Tuple of (static_content, variable_content) where:
            - static_content: System instructions and JSON schema (cacheable)
            - variable_content: GitHub URL and README content (variable)
        """
        schema = {
            "type": "function",
            "function": {
                "name": "create_mcp_server_manifest",
                "description": "Create a manifest file for an MCP server according to the schema",
                "parameters": {
                    "type": "object",
                    "required": ["display_name", "version",
                                 "repository", "license", "installations"],
                    "properties": {
                        "display_name": {"type": "string", "description": "Human-readable server name"},
                        "version": {"type": "string", "description": "Server version in semver format"},
                        "repository": {
                            "type": "object",
                            "required": ["type", "url"],
                            "properties": {
                                "type": {"type": "string", "enum": ["git"]},
                                "url": {"type": "string"}
                            }
                        },
                        "homepage": {"type": "string"},
                        "author": {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "url": {"type": "string"}
                            }
                        },
                        "license": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "arguments": {
                            "type": "object",
                            "description": "Configuration arguments required by the server",
                            "additionalProperties": {
                                "type": "object",
                                "required": ["description", "required"],
                                "properties": {
                                    "description": {"type": "string", "description": "Human-readable description of the argument"},
                                    "required": {"type": "boolean", "description": "Whether this argument is required"},
                                    "example": {"type": "string", "description": "Example value for this argument"}
                                }
                            }
                        },
                        "installations": {
                            "type": "object",
                            "description": "Different methods to install and run this server",
                            "additionalProperties": {
                                "type": "object",
                                "required": ["type", "command", "args"],
                                "properties": {
                                    "type": {"type": "string", "enum": ["npm", "python", "docker", "cli", "uvx", "custom"]},
                                    "command": {"type": "string", "description": "Command to run the server"},
                                    "args": {"type": "array", "description": "Arguments to pass to the command",
                                             "items": {"type": "string"}},
                                    "package": {"type": "string", "description": "Package name (for npm, pip, etc.)"},
                                    "env": {"type": "object", "description": "Environment variables to set",
                                            "additionalProperties": {"type": "string"}},
                                    "description": {"type": "string", "description": "Human-readable description"},
                                    "recommended": {"type": "boolean", "description": "Whether this is recommended"}
                                }
                            }
                        },
                        "examples": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "description", "prompt"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "prompt": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }

        static_content = (
            "You are a helpful assistant that analyzes GitHub README.md files.\n"
            "Extract information from the README and return it in JSON format.\n"
            "Use [NOT GIVEN] for missing information.\n\n"
            f"JSON Schema: {json.dumps(schema, indent=2)}\n\n"
        )

        variable_content = (
            f"GitHub URL: {repo_url}\n\n"
            f"README Content:\n{readme_content}\n\n"
            "Format the extracted information as JSON according to the schema."
        )

        return static_content, variable_content

    def _extract_with_llms(self, prompt: tuple[str, str]) -> Dict:
        """Extract manifest information using Amazon Bedrock with optimized caching.

        Args:
            prompt: Tuple of (static_content, variable_content) from _create_prompt

        Returns:
            Dictionary containing the extracted manifest information
        """
        static_content, variable_content = prompt

        try:
            response = self.client.converse(
                modelId=LLMModel.CLAUDE_3_7_SONNET,
                system=[
                    {"text": "You are a helpful assistant for README analysis."}
                ],
                messages=[{
                    "role": "user",
                    "content": [
                        {"text": static_content},
                        {"cachePoint": {"type": "default"}},
                        {"text": variable_content}
                    ]
                }],
                inferenceConfig={"temperature": 0.0}
            )

            # Remove debug output of full JSON response
            # Extract the text from the response with better error handling
            if 'output' in response and 'message' in response['output'] and 'content' in response['output']['message']:
                content = response['output']['message']['content']

                # Find the first text item
                text_items = [item.get('text')
                              for item in content if 'text' in item]
                if text_items:
                    try:
                        # Look for JSON content within the text
                        text_content = text_items[0]
                        # Try to extract JSON from the response text
                        # First check if it's already valid JSON
                        try:
                            return json.loads(text_content)
                        except json.JSONDecodeError:
                            # If not, try to find JSON in the text (it might be surrounded by other text)
                            import re
                            json_match = re.search(
                                r'(\{.*\})', text_content, re.DOTALL)
                            if json_match:
                                return json.loads(json_match.group(1))
                            else:
                                logger.error(
                                    f"No JSON content found in response: {text_content[:100]}...")
                                return self._get_minimal_manifest()
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(
                            f"Failed to parse JSON from response: {e}")
                else:
                    logger.error("No text items found in response content")
            else:
                logger.error(
                    f"Unexpected response structure: {response.keys()}")

            # If we get here, something went wrong with the parsing
            return self._get_minimal_manifest()

        except (KeyError, json.JSONDecodeError, StopIteration) as e:
            logger.error(f"Failed to process Bedrock response: {e}")
            return self._get_minimal_manifest()
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            return self._get_minimal_manifest()

    def _get_minimal_manifest(self) -> Dict:
        """Return a minimal valid manifest when extraction fails."""
        return {
            "name": "",
            "display_name": "",
            "version": "0.1.0",
            "description": "",
            "repository": {"type": "git", "url": ""},
            "license": "MIT",
            "installations": {},
            "tags": []
        }

    def generate_manifest(self, repo_url: str, server_name: Optional[str] = None) -> Dict:
        """Generate MCP server manifest from GitHub repository.

        Extracts information directly from the GitHub URL and README content.

        Args:
            repo_url: GitHub repository URL (uses default if None)
            server_name: Optional server name (derived from URL if None)

        Returns:
            MCP server manifest dictionary
        """
        # Extract repo info and fetch README
        repo_info = self.extract_repo_info(repo_url)
        readme_content = self.fetch_readme(repo_url)

        # Extract server info directly from URL
        server_info = self._extract_server_info_from_url(repo_url)

        # If no server name was explicitly provided, use the one from URL
        if not server_name:
            server_name = server_info['name']

        # If server info doesn't have a description, extract from README
        if not server_info['desc']:
            server_info['desc'] = self._extract_description_from_readme(
                readme_content)

        # Get prompt as tuple and extract manifest
        prompt = self._create_prompt(repo_url, readme_content)
        manifest = self._extract_with_llms(prompt)

        # Update manifest with repository information
        manifest.update({
            'name': server_name,
            'repository': {'type': 'git', 'url': repo_info['full_url']},
            'author': {'name': repo_info['owner']}
        })

        # Always set a default version if none is provided
        if not manifest.get('version') or manifest.get('version') == "[NOT GIVEN]":
            manifest['version'] = "0.1.0"

        # Enrich with description from README if not already meaningful
        if not manifest.get('description') or manifest.get('description') == "[NOT GIVEN]":
            manifest['description'] = server_info['desc']

        # Categorize the server
        sample_server = {
            "name": manifest.get("name", ""),
            "description": manifest.get("description", "")
        }

        categorized_servers = asyncio.run(
            self.categorize_servers([sample_server]))
        if categorized_servers:
            manifest["categories"] = [
                categorized_servers[0].get("category", "Unknown")]
            manifest["tags"] = manifest.get("tags", [])
            logger.info(f"Server categorized as: {manifest['categories'][0]}")

        return manifest


def main(repo_url: str):
    try:
        # Ensure the target directory exists
        os.makedirs("mcp-registry/servers", exist_ok=True)

        # Generate the manifest
        generator = ManifestGenerator()
        manifest = generator.generate_manifest(repo_url)

        # Ensure the manifest has a valid name
        if not manifest.get('name'):
            raise ValueError("Generated manifest is missing a name")

        # Save to mcp-registry/servers directory
        filename = f"mcp-registry/servers/{manifest['name']}.json"
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
