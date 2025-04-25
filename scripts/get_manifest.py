"""Generate MCP server manifests from GitHub repositories."""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

import dotenv
import requests
from categorization import CategorizationAgent
from openai import OpenAI
from utils import McpClient, inspect_docker_repo, validate_arguments_in_installation

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_OUTPUT_DIR = "mcp-registry/servers/"
DOCKER_MCP_REPO_URL = "https://hub.docker.com/r"


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
                if "![" in line or line.strip().startswith("[") or line.strip() == "" or line.strip().startswith(">"):
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
                        repo_name = repo_url.strip("/").split("/")[-1].lower()
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
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                completion = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": os.environ.get("SITE_URL", "https://mcpm.sh"),
                        "X-Title": "MCPM"
                    },
                    model="anthropic/claude-3-sonnet",
                    messages=[
                        {"role": "system",
                            "content": "Extract concise descriptions from README content."},
                        {
                            "role": "user",
                            "content": (
                                f"Extract a single concise description paragraph from this README "
                                f"content. Focus on what the project does, not how to use it. "
                                f"Keep it under 200 characters if possible:\n\n{readme_content}"
                            )
                        }
                    ],
                    temperature=0,
                    max_tokens=200
                )

                if not completion.choices or not completion.choices[0].message:
                    logger.warning(
                        f"Retry {retry_count+1}/{max_retries}: Empty completion response")
                    retry_count += 1
                    continue

                description = completion.choices[0].message.content.strip()

                # Validate the description
                if not description:
                    logger.warning(
                        f"Retry {retry_count+1}/{max_retries}: Empty description")
                    retry_count += 1
                    continue

                if len(description) < 10:
                    logger.warning(
                        f"Retry {retry_count+1}/{max_retries}: Description too short: {description}")
                    retry_count += 1
                    continue

                return description

            except Exception as e:
                logger.error(
                    f"Error extracting description with LLM (try {retry_count+1}/{max_retries}): {e}")
                retry_count += 1

        # If all retries failed, return empty string
        logger.error(
            f"All {max_retries} attempts to extract description failed")
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

        result = await agent.execute(server_name=name, server_description=description, include_examples=True)

        return result["category"]

    def extract_with_llms(self, repo_url: str, readme_content: str) -> Dict:
        """Extract manifest information using OpenAI with OpenRouter.

        Args:
            repo_url: GitHub repository URL
            readme_content: Content of the README file

        Returns:
            Dictionary containing the extracted manifest information
        """
        # Initialize the complete manifest dictionary
        complete_manifest = {}

        # Step 1: Extract basic information (display_name, license, tags)
        basic_info = self._extract_basic_info(repo_url, readme_content)
        complete_manifest.update(basic_info)

        # Step 2: Extract arguments
        arguments = self._extract_arguments(repo_url, readme_content)
        if arguments:
            complete_manifest["arguments"] = arguments

        # Step 3: Extract installations
        installations = self._extract_installations(repo_url, readme_content)
        if installations:
            # post process
            arguments = complete_manifest.get("arguments", {})
            if arguments:
                for install_type, installation in installations.items():
                    new_installation, replacement = validate_arguments_in_installation(installation, arguments)
                    if replacement:
                        installations[install_type] = new_installation
            complete_manifest["installations"] = installations

        # Step 4: Extract examples
        examples = self._extract_examples(repo_url, readme_content)
        if examples:
            complete_manifest["examples"] = examples

        return complete_manifest

    def _call_llm(self,
                  repo_url: str,
                  readme_content: str,
                  schema: Dict,
                  prompt: str) -> Dict:
        """Generic helper method to call LLM with common retry pattern.

        Args:
            repo_url: GitHub repository URL
            readme_content: README content
            schema: JSON schema for the function call
            prompt: User prompt for extraction
            system_prompt: System prompt for extraction

        Returns:
            Extracted information or default value if failed
        """
        system_prompt = "You are a helpful assistant that extracts information from a GitHub repository about a server."

        max_retries = 3
        retry_count = 0

        # Extract required fields from schema if available
        required_fields = schema.get("parameters", {}).get("required", [])

        while retry_count < max_retries:
            try:
                completion = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": os.environ.get("SITE_URL", "https://mcpm.sh"),
                        "X-Title": "MCPM"
                    },
                    model="anthropic/claude-3.7-sonnet",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": f"GitHub URL: {repo_url}\n\nREADME Content:\n{readme_content}\n\n{prompt}"
                        }
                    ],
                    tools=[{"type": "function", "function": schema}],
                    temperature=0,
                    tool_choice="required"
                )

                if not completion.choices or not completion.choices[0].message.tool_calls:
                    logger.warning(
                        f"Retry {retry_count+1}/{max_retries}: No tool calls in response")
                    retry_count += 1
                    continue

                tool_call = completion.choices[0].message.tool_calls[0]
                result = json.loads(tool_call.function.arguments)

                # Validate required fields if specified
                if required_fields:
                    missing_fields = [
                        field for field in required_fields if field not in result]
                    if missing_fields:
                        logger.warning(
                            f"Retry {retry_count+1}/{max_retries}: Missing fields: {missing_fields}")
                        retry_count += 1
                        continue

                return result

            except Exception as e:
                logger.error(
                    f"Error extracting data with LLM (try {retry_count+1}/{max_retries}): {e}")
                retry_count += 1

        logger.error(f"All {max_retries} attempts to extract data failed")

        return {field: None for field in required_fields}

    def _extract_basic_info(self, repo_url: str, readme_content: str) -> Dict:
        """Extract basic information (display_name, license, tags) using LLM."""
        schema = {
            "name": "extract_basic_info",
            "description": "Extract basic manifest information",
            "parameters": {
                "type": "object",
                "required": ["display_name", "tags"],
                "properties": {
                    "display_name": {
                        "type": "string",
                        "description": "Human-readable server name"
                    },
                    "license": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "additionalProperties": False
            },
        }

        return self._call_llm(
            repo_url=repo_url,
            readme_content=readme_content,
            schema=schema,
            prompt=("Extract the display_name, license, and tags from the README file. "
                    "The display_name should be a human-readable server name close to the name of the repository. "
                    "The tags should be a list of tags that describe the server.")
        )

    def _extract_arguments(self, repo_url: str, readme_content: str) -> Dict:
        """Extract arguments information using LLM."""
        schema = {
            "name": "extract_arguments",
            "description": "Extract arguments information",
            "required": ["arguments"],
            "parameters": {
                "type": "object",
                "properties": {
                    "arguments": {
                        "type": "array",
                        "description": "An array of configuration arguments required by the server",
                        "items": {
                            "type": "object",
                            "required": ["key", "description"],
                            "properties": {
                                "key": {
                                    "type": "string",
                                    "description": "The name of the argument"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Description of the argument"
                                },
                                "required": {
                                    "type": "boolean",
                                    "description": "Whether this argument is required"
                                },
                                "example": {
                                    "type": "string",
                                    "description": "Example value"
                                }
                            }
                        }
                    }
                }
            }
        }

        result = self._call_llm(
            repo_url=repo_url,
            readme_content=readme_content,
            schema=schema,
            prompt=("""Extract the configuration arguments required by this server from the README file.
The arguments should be a list of arguments that are required when running the server.
It can often be found in the usage section of the README file.
<Example>
<README> Docker
{
  "mcpServers": {
    "brave-search": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "BRAVE_API_KEY",
        "mcp/brave-search"
      ],
      "env": {
        "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
NPX
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-brave-search"
      ],
      "env": {
        "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
<README/>
From the example README, you should get:
{
  "arguments": [
    {
      "key": "BRAVE_API_KEY",
      "description": "The API key for the Brave Search server",
      "required": true,
      "example": "YOUR_API_KEY_HERE"
    }
  ]
}
<Example/>
if no arguments are required, return an empty array. """)
        )

        results = result.get("arguments", [])
        arguments = {}
        for result in results:
            arguments[result["key"]] = {
                "description": result.get("description", ""),
                "required": result.get("required", ""),
                "example": result.get("example", "")
            }

        return result.get("arguments", {})

    def _extract_installations(self, repo_url: str, readme_content: str) -> Dict:
        """Extract installations information using LLM."""
        schema = {
            "name": "extract_installations",
            "description": "Extract installation information for different clients(Claude Desktop/Cursor/Windsurf/VSCode and so on) from content inside of <README> tag and strictly follow the rules",
            "required": ["installations"],
            "parameters": {
                "type": "object",
                "properties": {
                    "installations": {
                        "type": "array",
                        "description": "An array of methods to install and run this server",
                        "items": {
                            "type": "object",
                            "required": ["type", "command", "args"],
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["npm", "python", "docker", "cli", "uvx", "custom"]
                                },
                                "command": {
                                    "type": "string",
                                    "description": "Command to run the server"
                                },
                                "args": {
                                    "type": "array",
                                    "description": "Arguments for the command",
                                    "items": {"type": "string"}
                                },
                                "env": {
                                    "type": "object",
                                    "description": "Environment variables",
                                    "additionalProperties": {"type": "string"},
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Human-readable description"
                                }
                            }
                        }
                    }
                }
            }
        }

        result = self._call_llm(
            repo_url=repo_url,
            readme_content=readme_content,
            schema=schema,
            prompt=(
                """Extract the installation information of different clients for this server.
The installations should be a list of methods to install and run this server.
It can often be found in the usage section with **valid json format** of the README file.
<RULES>
1. Skip any method using '@smithery/cli' or similar Smithery CLI tools.
2. Only focus on json block and exclude other blocks like bash/sh/code
3. The command should be one of the following: npx, uvx, node, docker, python, bunx, deno. Don't include other commands
4. If multiple installations exist, exclude local/deployment/debug configuration, only keep uvx, npx, docker
</RULES>
<Example>
<README> Docker
{
  "mcpServers": {
    "brave-search": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "BRAVE_API_KEY",
        "mcp/brave-search"
      ],
      "env": {
        "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
NPX
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-brave-search"
      ],
      "env": {
        "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
</README>
From the example README, you should get:
{
  "installations": [
    {
      "type": "docker",
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "BRAVE_API_KEY",
        "mcp/brave-search"
      ],
      "env": {
        "BRAVE_API_KEY": "${{YOUR_API_KEY_HERE}}"
      }
    },
    {
      "type": "npm",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-brave-search"
      ],
      "env": {
        "BRAVE_API_KEY": "${{YOUR_API_KEY_HERE}}"
      }
    }
  ]
}
</Example>
Note that installation type should be one of the following: npm, python, docker, cli, uvx, custom.
For placeholder variables, use ${...} to indicate the variable.
If no installations are provided, return an empty array. """)

        )

        results = result.get("installations", [])
        installations = {}
        for result in results:
            installations[result["type"]] = result

        return installations

    def _extract_examples(self, repo_url: str, readme_content: str) -> list:
        """Extract examples information using LLM."""
        schema = {
            "name": "extract_examples",
            "description": "Extract examples prompts that can be used to test the server",
            "required": ["example_prompts"],
            "parameters": {
                "type": "object",
                "properties": {
                    "example_prompts": {
                        "type": "array",
                        "description": "An array of examples prompts that can be used to test the server",
                        "items": {
                            "type": "string",
                            "description": "A prompt that can be used to test the server"
                        }
                    }
                }
            }
        }

        result = self._call_llm(
            repo_url=repo_url,
            readme_content=readme_content,
            schema=schema,
            prompt=("""Extract usage examples for this server.
The examples should be a short list of examples prompts that can be used to test the server.
If no examples are provided, return an empty array.
""")
        )

        result = result.get("example_prompts", [])
        examples = []
        for prompt in result:
            examples.append({
                "title": "",
                "description": "",
                "prompt": prompt
            })
        return examples

    def generate_manifest(self, repo_url: str, server_name: Optional[str] = None) -> Dict:
        """Generate MCP server manifest from GitHub repository.

        Extracts information directly from the GitHub URL and README content.

        Args:
            repo_url: GitHub repository URL(uses default if None)
            server_name: Optional server name(derived from URL if None)

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
            manifest.update(
                {
                    "name": name,
                    "repository": {"type": "git", "url": repo_url},
                    "homepage": repo_url,
                    "author": {"name": owner},
                }
            )

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
                logger.info(f"Server categorized as: {categorized_category}")
                manifest["categories"] = [categorized_category]
            else:
                logger.error(f"Server not categorized: {name} - {description}")

            # Sort installations by priority
            manifest["installations"] = self.filter_and_sort_installations(
                manifest.get("installations", {}))

            # Extract capabilities if installations are available
            if manifest["installations"]:
                logger.info(
                    f"Server installations: {manifest['installations']}")
                try:
                    capabilities = asyncio.run(
                        self.run_server_and_extract_capabilities(manifest))
                    if capabilities:
                        manifest.update(capabilities)
                except Exception as e:
                    logger.error(f"Failed to extract capabilities: {e}")

            # docker url if docker command in installation
            installations = manifest.get("installations", {})
            if "docker" in installations:
                docker_repo_name = inspect_docker_repo(installations["docker"])
                if docker_repo_name:
                    manifest["docker_url"] = f"{DOCKER_MCP_REPO_URL}/{docker_repo_name}"

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
        # Check if installations is a dictionary
        if not isinstance(installations, dict):
            logger.error(
                f"Expected dictionary for installations, got {type(installations)}: {installations}")
            return {}

        priority = {"uvx": 0, "npm": 1, "python": 2,
                    "docker": 3, "cli": 4, "custom": 5}
        filtered_installations = {k: v for k,
                                  v in installations.items() if k in priority}
        sorted_installations = sorted(
            filtered_installations.items(), key=lambda x: priority.get(x[0], 6))
        return dict(sorted_installations)


def main(repo_url: str, is_official: bool = False, output_dir: str = _OUTPUT_DIR):
    try:
        # Generate the manifest
        generator = ManifestGenerator()
        manifest = generator.generate_manifest(repo_url)
        manifest["is_official"] = is_official

        # Ensure the manifest has a valid name
        if not manifest.get("name") or not manifest.get("author", {}).get("name"):
            raise ValueError(
                "Generated manifest is missing a name and/or author name")

        # determine the filename
        filename = os.path.join(output_dir, f"{manifest['name']}_new.json")
        if not is_official:
            name = f"@{manifest['author']['name']}/{manifest['name']}"
            filename = os.path.join(output_dir, f"{manifest['name']}@{manifest['author']['name']}.json")
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
        logger.error(
            "Usage: python script.py <github-url> or python script.py test")
        sys.exit(1)

    repo_url = sys.argv[1].strip()

    output_dir = _OUTPUT_DIR
    if repo_url == "test":
        # overwrite global output directory
        output_dir = "local/servers/"

    os.makedirs(output_dir, exist_ok=True)

    if repo_url == "test":
        # run through all the test cases
        repo_urls = [
            "https://github.com/modelcontextprotocol/servers/tree/main/src/time",
            "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
            "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
            "https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking",
            "https://github.com/modelcontextprotocol/servers/tree/main/src/sentry"
        ]

        for repo_url in repo_urls:
            logger.info(f"Processing GitHub URL: {repo_url}")
            main(repo_url, is_official=True, output_dir=output_dir)
    else:
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

        main(repo_url, is_official, output_dir)
