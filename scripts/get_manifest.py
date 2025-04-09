"""Generate MCP server manifests from GitHub repositories."""

import os
import sys
from typing import Any, Dict, List, Optional

import json
import asyncio
import requests
from openai import OpenAI
from loguru import logger
from utils import McpClient
from categorization import CategorizationAgent

import dotenv
dotenv.load_dotenv()


class ManifestGenerator:
    """Generate and manage MCP server manifests from GitHub repositories."""

    def __init__(self):
        """Initialize with OpenAI client."""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )

    def extract_description_from_readme(self, readme_content: str, repo_url: str = "") -> str:
        """Extract a concise description from README content.

        Looks for the first meaningful description paragraph near the beginning
        of the README, typically after the title. Skips badges, links, and
        code blocks.

        Args:
            readme_content: Contents of README.md
            repo_url: GitHub repository URL to extract name for title matching

        Returns:
            Extracted description or empty string if not found
        """
        try:
            # Split readme into lines
            lines = readme_content.split("\n")
            description = ""
            in_code_block = False
            in_html_block = False
            title_content = {}  # Store content under headings

            current_heading = None

            for i, line in enumerate(lines):
                # Track headings and their content
                if line.strip().startswith("#"):
                    current_heading = line.strip().lstrip("#").strip()
                    title_content[current_heading] = []
                    continue

                if current_heading:
                    title_content[current_heading].append(line)

                # Skip code blocks
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue

                # Skip HTML blocks
                if line.strip().startswith("<"):
                    in_html_block = True
                    continue
                if in_html_block and line.strip().endswith(">"):
                    in_html_block = False
                    continue
                if in_html_block:
                    continue

                # Skip badges, links, and empty lines
                if ("![" in line or
                    line.strip().startswith("[") or
                    line.strip() == "" or
                        line.strip().startswith(">")):
                    continue

                # Found a potential description line
                if len(line.strip()) > 20:  # Reasonable length for description
                    description = line.strip()
                    break

            # If we couldn't find a good description in regular text,
            # check content under main repo name heading
            if not description and repo_url:
                for heading, content in title_content.items():
                    # Look for the repo name in the heading
                    if heading:
                        repo_name = repo_url.strip('/').split('/')[-1].lower()
                        if repo_name.lower() in heading.lower():
                            for line in content:
                                if len(line.strip()) > 20 and "![" not in line:
                                    description = line.strip()
                                    break
                            if description:
                                break

            # If we couldn't find a good description, return empty string
            if not description:
                logger.warning("No description found in README")
                return ""
            else:
                logger.info(f"Extracted description: {description}")
                return description

        except Exception as e:
            logger.error(f"Error extracting description from README: {e}")
            return ""

    def extract_description_from_readme_with_llms(self, readme_content: str) -> str:
        """Extract a concise description from README content using LLM."""
        try:
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": os.environ.get("SITE_URL", "https://mcpm.sh"),
                    "X-Title": "MCPM",
                },
                model="anthropic/claude-3-sonnet",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts concise descriptions."
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Extract a single concise description paragraph from this README "
                            f"content. Focus on what the project does, not how to use it. "
                            f"Keep it under 200 characters if possible:\n\n{readme_content}"
                        )
                    }
                ],
                temperature=0.1,
                max_tokens=200
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error extracting description with LLM: {e}")
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
        try:
            raw_url = self._convert_to_raw_url(repo_url)
            response = requests.get(raw_url)

            if response.status_code != 200 and "main" in raw_url:
                logger.warning(
                    f"Failed to fetch README.md from {repo_url} with {raw_url}. Status code: {response.status_code}"
                )
                raw_url = raw_url.replace("/main/", "/master/")
                response = requests.get(raw_url)

            if response.status_code != 200:
                raise ValueError(
                    f"Failed to fetch README.md from {repo_url} with {raw_url}. Status code: {response.status_code}"
                )

            return response.text
        except Exception as e:
            logger.error(f"Error fetching README from {repo_url}: {e}")
            return ""

    def _convert_to_raw_url(self, repo_url: str) -> str:
        """Convert GitHub URL to raw content URL for README.md."""
        if "github.com" not in repo_url:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        # Handle subdirectory URLs (tree format)
        if "/tree/" in repo_url:
            # For URLs like github.com/user/repo/tree/branch/path/to/dir
            parts = repo_url.split("/tree/")
            base_url = parts[0].replace(
                "github.com", "raw.githubusercontent.com")
            path_parts = parts[1].split("/", 1)

            if len(path_parts) > 1:
                branch = path_parts[0]
                subdir = path_parts[1]
                return f"{base_url}/{branch}/{subdir}/README.md"
            else:
                branch = path_parts[0]
                return f"{base_url}/{branch}/README.md"

        # Handle direct file URLs
        if "/blob/" in repo_url:
            raw_url = repo_url.replace("/blob/", "/raw/")
            if raw_url.endswith(".md"):
                return raw_url
            else:
                return f"{raw_url}/README.md"

        # Handle repository root URLs
        raw_url = repo_url.replace("github.com", "raw.githubusercontent.com")
        return f"{raw_url.rstrip('/')}/main/README.md"

    @staticmethod
    async def categorize_servers_with_llms(name, description) -> str:
        """Categorize a server based on name and description.

        Args:
            name: Server name
            description: Server description

        Returns:
            Category string
        """
        agent = CategorizationAgent()

        result = await agent.execute(
            server_name=name, server_description=description, include_examples=True
        )

        return result['category']

    @staticmethod
    def _create_prompt(repo_url: str, readme_content: str) -> tuple[str, str]:
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
                    "required": ["display_name", "repository", "license", "installations"],
                    "properties": {
                        "display_name": {"type": "string", "description": "Human-readable server name"},
                        "license": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "arguments": {
                            "type": "object",
                            "description": "Configuration arguments required by the server",
                            "additionalProperties": {
                                "type": "object",
                                "required": ["description", "required"],
                                "properties": {
                                    "description": {
                                        "type": "string",
                                        "description": "Human-readable description of the argument",
                                    },
                                    "required": {"type": "boolean", "description": "Whether this argument is required"},
                                    "example": {"type": "string", "description": "Example value for this argument"},
                                },
                            },
                        },
                        "installations": {
                            "type": "object",
                            "description": "Different methods to install and run this server",
                            "additionalProperties": {
                                "type": "object",
                                "required": ["type", "command", "args"],
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["npm", "python", "docker", "cli", "uvx", "custom"],
                                    },
                                    "command": {"type": "string", "description": "Command to run the server"},
                                    "args": {
                                        "type": "array",
                                        "description": "Arguments to pass to the command",
                                        "items": {"type": "string"},
                                    },
                                    "env": {
                                        "type": "object",
                                        "description": "Environment variables to set",
                                        "additionalProperties": {"type": "string"},
                                    },
                                    "description": {"type": "string", "description": "Human-readable description"},
                                },
                            },
                        },
                        "examples": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "description", "prompt"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "prompt": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
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

    def extract_with_llms(self, repo_url: str, readme_content: str) -> Dict:
        """Extract manifest information using OpenAI with OpenRouter.

        Args:
            repo_url: GitHub repository URL
            readme_content: Content of the README file

        Returns:
            Dictionary containing the extracted manifest information
        """
        try:
            static_content, variable_content = self._create_prompt(
                repo_url, readme_content)

            schema = {
                "name": "create_mcp_server_manifest",
                "description": "Create a manifest file for an MCP server according to the schema",
                "parameters": {
                    "type": "object",
                    "required": ["display_name", "repository", "license", "installations"],
                    "properties": {
                        "display_name": {"type": "string", "description": "Human-readable server name"},
                        "license": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "arguments": {
                            "type": "object",
                            "description": "Configuration arguments required by the server",
                            "additionalProperties": {
                                "type": "object",
                                "required": ["description", "required"],
                                "properties": {
                                    "description": {
                                        "type": "string",
                                        "description": "Human-readable description of the argument",
                                    },
                                    "required": {"type": "boolean", "description": "Whether this argument is required"},
                                    "example": {"type": "string", "description": "Example value for this argument"},
                                },
                            },
                        },
                        "installations": {
                            "type": "object",
                            "description": "Different methods to install and run this server",
                            "additionalProperties": {
                                "type": "object",
                                "required": ["type", "command", "args"],
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["npm", "python", "docker", "cli", "uvx", "custom"],
                                    },
                                    "command": {"type": "string", "description": "Command to run the server"},
                                    "args": {
                                        "type": "array",
                                        "description": "Arguments to pass to the command",
                                        "items": {"type": "string"},
                                    },
                                    "env": {
                                        "type": "object",
                                        "description": "Environment variables to set",
                                        "additionalProperties": {"type": "string"},
                                    },
                                    "description": {"type": "string", "description": "Human-readable description"},
                                },
                            },
                        },
                        "examples": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "description", "prompt"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "prompt": {"type": "string"},
                                },
                            },
                        },
                    }
                }
            }

            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": os.environ.get("SITE_URL", "https://mcpm.sh"),
                    "X-Title": "MCPM",
                },
                model="anthropic/claude-3-sonnet",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes GitHub README.md files and extracts information for MCP server manifests."
                    },
                    {
                        "role": "user",
                        "content": f"GitHub URL: {repo_url}\n\nREADME Content:\n{readme_content}\n\nExtract the necessary information to create an MCP server manifest."
                    }
                ],
                tools=[{"type": "function", "function": schema}],
                tool_choice={"type": "function", "function": {
                    "name": "create_mcp_server_manifest"}}
            )

            tool_call = completion.choices[0].message.tool_calls[0]
            result = json.loads(tool_call.function.arguments)
            return result
        except Exception as e:
            logger.error(f"Error extracting manifest with LLM: {e}")
            return {}

    def generate_manifest(self, repo_url: str, server_name: Optional[str] = None) -> Dict:
        """Generate MCP server manifest from GitHub repository.

        Extracts information directly from the GitHub URL and README content.

        Args:
            repo_url: GitHub repository URL (uses default if None)
            server_name: Optional server name (derived from URL if None)

        Returns:
            MCP server manifest dictionary
        """
        try:
            # Extract repo info
            parts = repo_url.strip("/").split("/")
            owner = parts[3]

            # Extract name, handling subdirectories in tree format
            if "/tree/" in repo_url and "/src/" in repo_url:
                # For subdirectories in the src folder, use the subdirectory name
                src_path = repo_url.split("/src/")[1]
                name = src_path.split("/")[0]
            else:
                # Default is the last path component
                name = parts[-1]

            # If no server name was explicitly provided, use the one from URL
            if server_name:
                name = server_name

            # Fetch README content
            readme_content = self.fetch_readme(repo_url)

            # Get prompt as tuple and extract manifest
            manifest = self.extract_with_llms(repo_url, readme_content)
            # Update manifest with repository information
            manifest.update({
                "name": name,
                "repository": {"type": "git", "url": repo_url},
                "homepage": repo_url,
                "author": {"name": owner},
            })

            # Update manifest with description
            description = self.extract_description_from_readme(
                readme_content, repo_url)
            if not description:
                description = self.extract_description_from_readme_with_llms(
                    readme_content)
            manifest["description"] = description

            # Categorize the server
            categorized_category = asyncio.run(
                self.categorize_servers_with_llms(name, description))
            if categorized_category:
                logger.info(
                    f"Server categorized as: {categorized_category}")
                manifest["categories"] = [categorized_category]
            else:
                logger.error(
                    f"Server not categorized: {name} - {description}")

            # Sort installations by priority
            manifest["installations"] = self.filter_and_sort_installations(
                manifest.get("installations", {})
            )

            # Extract capabilities if installations are available
            if manifest["installations"]:
                logger.info(
                    f"Server installations: {manifest['installations']}")
                try:
                    capabilities = asyncio.run(
                        self.run_server_and_extract_capabilities(manifest)
                    )
                    if capabilities:
                        manifest.update(capabilities)
                except Exception as e:
                    logger.error(f"Failed to extract capabilities: {e}")

            return manifest

        except Exception as e:
            logger.error(f"Error generating manifest: {e}")
            return {
                "name": "",
                "display_name": "",
                "description": "",
                "repository": {"type": "git", "url": ""},
                "license": "MIT",
                "installations": {},
                "tags": [],
            }

    @staticmethod
    async def run_server_and_extract_capabilities(manifest: dict[str, Any]) -> dict:
        """Run server and extract its capabilities.

        Args:
            manifest: Server manifest with installation instructions

        Returns:
            Dictionary with extracted capabilities
        """
        if not manifest.get("installations"):
            return {}

        mcp_client = McpClient()
        installation = list(manifest.get("installations", {}).values())[0]
        envs = installation.get("env", {})
        env_vars = {}

        if envs:
            for k, v in envs.items():
                env_vars[k] = manifest.get("arguments", {}).get(
                    k, {}).get("example", v)

        # Use the command and args from the installation directly
        command = installation["command"]
        args = installation["args"]

        await mcp_client.connect_to_server(command, args, env_vars)
        result = {}

        try:
            tools = await mcp_client.list_tools()
            # to avoid $schema field
            result["tools"] = [json.loads(tool.model_dump_json())
                               for tool in tools.tools]

            prompts = await mcp_client.list_prompts()
            result["prompts"] = [json.loads(
                prompt.model_dump_json()) for prompt in prompts.prompts]

            resources = await mcp_client.list_resources()
            result["resources"] = [json.loads(
                resource.model_dump_json()) for resource in resources.resources]

        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return {}

        finally:
            await mcp_client.close()

        return result

    @staticmethod
    def filter_and_sort_installations(installations: dict[str, dict[str, Any]]) -> dict:
        """Filter and sort installation methods by priority.

        Args:
            installations: Dictionary of installation methods

        Returns:
            Sorted dictionary of installation methods
        """
        priority = {"uvx": 0, "npm": 1, "python": 2,
                    "docker": 3, "cli": 4, "custom": 5}
        filtered_installations = {k: v for k,
                                  v in installations.items() if k in priority}
        sorted_installations = sorted(
            filtered_installations.items(), key=lambda x: priority.get(x[0], 6))
        return dict(sorted_installations)


def main(repo_url: str, is_official: bool = False):
    try:
        # Ensure the target directory exists
        os.makedirs("mcp-registry/servers", exist_ok=True)

        # Generate the manifest
        generator = ManifestGenerator()
        manifest = generator.generate_manifest(repo_url)
        manifest["is_official"] = is_official

        # Ensure the manifest has a valid name
        if not manifest.get("name") or not manifest.get("author", {}).get("name"):
            raise ValueError(
                "Generated manifest is missing a name and/or author name")

        # determine the filename
        filename = f"mcp-registry/servers/{manifest['name']}.json"
        if not is_official:
            name = f"@{manifest['author']['name']}/{manifest['name']}"
            filename = (
                f"mcp-registry/servers/{manifest['name']}@{manifest['author']['name']}.json"
            )
            manifest["name"] = name

        # save the manifest with the determined filename
        if os.path.exists(filename):
            logger.warning(
                f"Official manifest already exists: {filename}. Overwriting...")
        with open(filename, "w", encoding="utf-8") as file:
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
    # Check if the URL is a simple URL without protocol
    if not repo_url.startswith(("http://", "https://")):
        # Add https:// if it's a github.com URL without protocol
        if repo_url.startswith("github.com"):
            repo_url = "https://" + repo_url
        # Check if it's a full URL without protocol
        else:
            logger.error("Error: URL must be a GitHub URL")
            sys.exit(1)

    parts = repo_url.strip("/").split("/")

    if len(parts) < 5 or parts[2] != "github.com":
        logger.error(f"Not a valid GitHub URL: {repo_url}")
        sys.exit(1)

    if parts[3] == "modelcontextprotocol":
        is_official = True
    else:
        is_official = False

    # Initialize logger only once to avoid duplicate logs
    logger.info(f"Processing GitHub URL: {repo_url}")

    main(repo_url, is_official)
