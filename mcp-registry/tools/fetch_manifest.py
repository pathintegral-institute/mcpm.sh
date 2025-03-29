import json
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional, Literal
from openai import OpenAI, pydantic_function_tool
from pydantic import BaseModel, Field
import requests
import tqdm

load_dotenv()


task_prompt = """
You are a helpful assistant that can view the content use browser, 
You will be given a github url and you need to open it in the browser.
then you need to extract the information from the readme.md file and return it in json format.
If info is not provided, input [NOT GIVEN].
DON'T STEP INTO OTHER URLS, the readme.md file is just provided in the url. Scroll down until you read the full content.

The json schema: 
<json_schema>
{
    "name": "create_mcp_server_manifest",
    "description": "Create a manifest file for an MCP server according to the schema",
    "parameters": {
        "type": "object",
        "required": [
            "name",
            "display_name",
            "version",
            "description",
            "repository",
            "license",
                "installations"
            ],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Server name in kebab-case format"
                },
                "display_name": {
                    "type": "string",
                    "description": "Human-readable server name"
                },
                "version": {
                    "type": "string",
                    "description": "Server version in semver format"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of the server's functionality"
                },
                "repository": {
                    "type": "object",
                    "required": ["type", "url"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["git"]
                        },
                        "url": {
                            "type": "string"
                        }
                    }
                },
                "homepage": {
                    "type": "string"
                },
                "author": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "email": {
                            "type": "string"
                        },
                        "url": {
                            "type": "string"
                        }
                    }
                },
                "license": {
                    "type": "string"
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "arguments": {
                    "type": "object",
                    "description": "Configuration arguments required by the server",
                    "additionalProperties": {
                        "type": "object",
                        "required": ["description", "required"],
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Human-readable description of the argument"
                            },
                            "required": {
                                "type": "boolean",
                                "description": "Whether this argument is required for the server to function"
                            },
                            "example": {
                                "type": "string",
                                "description": "Example value for this argument"
                            }
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
                            "type": {
                                "type": "string",
                                "description": "Type of installation method",
                                "enum": ["npm", "python", "docker", "cli", "uvx", "custom"]
                            },
                            "command": {
                                "type": "string",
                                "description": "Command to run the server"
                            },
                            "args": {
                                "type": "array",
                                "description": "Arguments to pass to the command",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "package": {
                                "type": "string",
                                "description": "Package name (for npm, pip, etc.)"
                            },
                            "env": {
                                "type": "object",
                                "description": "Environment variables to set",
                                "additionalProperties": {
                                    "type": "string"
                                }
                            },
                            "description": {
                                "type": "string",
                                "description": "Human-readable description of this installation method"
                            },
                            "recommended": {
                                "type": "boolean",
                                "description": "Whether this is the recommended installation method"
                            }
                        }
                    }
                },
                "examples": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "description", "prompt"],
                        "properties": {
                            "title": {
                                "type": "string"
                            },
                            "description": {
                                "type": "string"
                            },
                            "prompt": {
                                "type": "string"
                            }
                        }
                    }
                }
            }
        }
    }
</json_schema>
<github_url>
%s
</github_url>
"""

# Pydantic models for MCP Server Manifest
class RepositoryModel(BaseModel):
    type: Literal["git"] = Field(description="Repository type")
    url: str = Field(description="Repository URL")

class AuthorModel(BaseModel):
    name: str = Field(description="Author name")
    email: Optional[str] = Field(None, description="Author email")
    url: Optional[str] = Field(None, description="Author URL")

class ArgumentModel(BaseModel):
    description: str = Field(description="Human-readable description of the argument")
    required: bool = Field(description="Whether this argument is required for the server to function")
    example: Optional[str] = Field(None, description="Example value for this argument")

class InstallationModel(BaseModel):
    type: Literal["npm", "python", "docker", "cli", "uvx", "custom"] = Field(
        description="Type of installation method"
    )
    command: str = Field(description="Command to run the server")
    args: List[str] = Field(description="Arguments to pass to the command")
    package: Optional[str] = Field(None, description="Package name (for npm, pip, etc.)")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables to set")
    description: Optional[str] = Field(None, description="Human-readable description of this installation method")
    recommended: Optional[bool] = Field(None, description="Whether this is the recommended installation method")

class ExampleModel(BaseModel):
    title: str
    description: str
    prompt: str

class MCPServerManifest(BaseModel):
    """Model for MCP Server Manifest according to the schema"""
    name: str = Field(description="Server name in kebab-case format")
    display_name: str = Field(description="Human-readable server name")
    version: str = Field(description="Server version in semver format")
    description: str = Field(description="Brief description of the server's functionality")
    repository: RepositoryModel
    homepage: Optional[str] = None
    author: Optional[AuthorModel] = None
    license: str
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    arguments: Optional[Dict[str, ArgumentModel]] = Field(
        None, description="Configuration arguments required by the server"
    )
    installations: Dict[str, InstallationModel] = Field(
        description="Different methods to install and run this server"
    )
    examples: Optional[List[ExampleModel]] = None

def get_all_servers():
    """
    Read content from all_servers.md, parse each line, and return structured data.
    
    Returns:
        list: A list of dictionaries with keys 'name', 'url', and 'desc' for each server.
    """
    # Path to the all_servers.md file
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'all_servers.md')
    
    # List to store the parsed servers
    servers = []
    
    # Read the file line by line
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check if the line starts with a list marker and contains a link
            if line.startswith('*') and '[' in line and '](' in line and ')' in line:
                # Find the positions of the markdown elements
                name_start = line.find('[') + 1
                name_end = line.find(']')
                
                # Check if we found valid positions
                if name_start > 0 and name_end > name_start:
                    display_name = line[name_start:name_end].strip()
                    
                    url_start = line.find('(', name_end) + 1
                    url_end = line.find(')', url_start)
                    
                    # Check if we found valid positions
                    if url_start > 0 and url_end > url_start:
                        url = line[url_start:url_end].strip()
                        
                        # Find the description after the URL
                        desc_part = line[url_end + 1:].strip()
                        
                        # Check if there's a hyphen after the closing bracket or asterisks
                        if '**' in desc_part and ' - ' in desc_part:
                            desc_start = desc_part.find(' - ') + 3
                            description = desc_part[desc_start:].strip()
                        elif ' - ' in desc_part:
                            desc_start = desc_part.find(' - ') + 3
                            description = desc_part[desc_start:].strip()
                        else:
                            # If no hyphen, take everything after the closing bracket and asterisks
                            if '**' in desc_part:
                                desc_start = desc_part.find('**') + 2
                                description = desc_part[desc_start:].strip()
                            else:
                                description = desc_part.strip()
                        
                        # Convert display name to kebab-case
                        name = display_name.lower()
                        # Replace non-alphanumeric characters with hyphens
                        name = ''.join(char if char.isalnum() else '-' for char in name)
                        # Remove leading and trailing hyphens
                        name = name.strip('-')
                        # Replace multiple hyphens with a single one
                        while '--' in name:
                            name = name.replace('--', '-')
                        
                        servers.append({
                            "name": name,
                            "url": url,
                            "desc": description
                        })
    
    return servers


def function_tool():
    """
    Convert the manifest schema to an OpenAI tool call format.
    
    Returns:
        dict: The schema in OpenAI tool call format.
    """
    return {
        "type": "function",
        "function": {
            "name": "create_mcp_server_manifest",
            "description": "Create a manifest file for an MCP server according to the schema",
            "parameters": {
                "type": "object",
                "required": [
                    "name",
                    "display_name",
                    "version",
                    "description",
                    "repository",
                    "license",
                    "installations"
                ],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Server name in kebab-case format"
                    },
                    "display_name": {
                        "type": "string",
                        "description": "Human-readable server name"
                    },
                    "version": {
                        "type": "string",
                        "description": "Server version in semver format"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the server's functionality"
                    },
                    "repository": {
                        "type": "object",
                        "required": ["type", "url"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["git"]
                            },
                            "url": {
                                "type": "string"
                            }
                        }
                    },
                    "homepage": {
                        "type": "string"
                    },
                    "author": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {
                                "type": "string"
                            },
                            "email": {
                                "type": "string"
                            },
                            "url": {
                                "type": "string"
                            }
                        }
                    },
                    "license": {
                        "type": "string"
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Configuration arguments required by the server",
                        "additionalProperties": {
                            "type": "object",
                            "required": ["description", "required"],
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "Human-readable description of the argument"
                                },
                                "required": {
                                    "type": "boolean",
                                    "description": "Whether this argument is required for the server to function"
                                },
                                "example": {
                                    "type": "string",
                                    "description": "Example value for this argument"
                                }
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
                                "type": {
                                    "type": "string",
                                    "description": "Type of installation method",
                                    "enum": ["npm", "python", "docker", "cli", "uvx", "custom"]
                                },
                                "command": {
                                    "type": "string",
                                    "description": "Command to run the server"
                                },
                                "args": {
                                    "type": "array",
                                    "description": "Arguments to pass to the command",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "package": {
                                    "type": "string",
                                    "description": "Package name (for npm, pip, etc.)"
                                },
                                "env": {
                                    "type": "object",
                                    "description": "Environment variables to set",
                                    "additionalProperties": {
                                        "type": "string"
                                    }
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Human-readable description of this installation method"
                                },
                                "recommended": {
                                    "type": "boolean",
                                    "description": "Whether this is the recommended installation method"
                                }
                            }
                        }
                    },
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "description", "prompt"],
                            "properties": {
                                "title": {
                                    "type": "string"
                                },
                                "description": {
                                    "type": "string"
                                },
                                "prompt": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def extract_json_from_markdown(markdown):
    openai = OpenAI()
    sys_prompt = """You are an outstanding assistant that can extract information from markdown files.
    the json will be used in the provided tool call. If you can't extract the information, input [NOT GIVEN].
    The installation method can be found in the markdown file, quoted by ```.
    MAKE SURE TO INCLUDE INSTALLATIONS IN RESULT.
    Don't hallucinate.
    """
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": markdown}
    ]
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=[function_tool()],
        tool_choice="required",
    )
    return response.choices[0].message.tool_calls[0].function.arguments


def main():
    servers = get_all_servers()
    servers_mapping = {server['name']: server for server in servers}

    # refetch_readme(servers_mapping)

    # fetch_readme(servers)
    for path, markdown in read_markdowns():
        name = path.split('.')[0]
        if os.path.exists(f'mcp-registry/servers/{name}.json'):
            print(f"Server {name} generated")
            continue
        if not is_valid_markdown(markdown):
            print(f"Invalid markdown for {name}")
            continue
        parsed = json.loads(extract_json_from_markdown(markdown))
        parsed['name'] = name
        parsed['description'] = servers_mapping[name]['desc']
        parsed['repository']['url'] = servers_mapping[name]['url']
        with open('mcp-registry/servers/' + name + '.json', 'w') as f:
            f.write(json.dumps(parsed, indent=2))

def is_valid_markdown(markdown):
    if not markdown.startswith('#') and '<!DOCTYPE html>' in markdown:
        return False
    return True

def read_markdowns():
    paths = os.listdir('downloads')
    for path in paths:
        print(path)
        with open(f'downloads/{path}', 'r') as f:
            markdown = f.read()
            yield path, markdown

def refetch_readme(servers_mapping):
    todo_servers = []
    for path, markdown in read_markdowns():
        if not is_valid_markdown(markdown):
            todo_servers.append(servers_mapping[path.split('.')[0]])
    fetch_readme(todo_servers)

def fetch_readme(servers):
    failed = []
    for server in tqdm.tqdm(servers):
        if 'blob' in server['url']:
            url = server['url'].replace('blob', 'raw') + '/README.md'
        else:
            url = server['url'] + '/raw/main/README.md'
        print(server, url)
        response = requests.get(url)
        if not is_valid_markdown(response.text):
            url = url.replace('/main/', '/master/')
            response = requests.get(url)
        if response.text == 'Not Found':
            failed.append(server)
            continue
        with open(f'downloads/{server["name"]}.md', 'w') as f:
            f.write(response.text)
    if failed:
        with open('Downloads/failed.json', 'w') as f:
            f.write(json.dumps(failed, indent=2))
        print(failed)
        

def extract_author_repo_from_gh_url(url):
    splits = url.split('/')
    return splits[3], 'https://github.com/' + splits[3] + '/' + splits[4]

def fix_server_url():
    white_lists = ['github', 'time', 'everything']
    servers = get_all_servers()
    servers_mapping = {server['name']: server for server in servers}
    server_paths = os.listdir('mcp-registry/servers')
    for path in tqdm.tqdm(server_paths):
        if path.split('.')[0] in white_lists:
            continue
        with open(f'mcp-registry/servers/{path}', 'r') as f:
            manifest = json.load(f)
        author, repo = extract_author_repo_from_gh_url(servers_mapping[path.split('.')[0]]['url'])
        manifest['repository']['url'] = repo
        manifest['author'] = {'name': author}
        manifest['homepage'] = servers_mapping[path.split('.')[0]]['url']
        with open(f'mcp-registry/servers/{path}', 'w') as f:
            json.dump(manifest, f, indent=2)

def fix_installation_param(markdown, json_manifest):
    client = OpenAI()
    sys_prompt = """
    You are an outstanding assistant who can helps to complete the json installation param.
    You will be given a readme file and a json manifest generated from the file.
    You need to check the `installations` part from the given json, 
    and confirm if there is some example params like "Your API KEY", "example.key", "http://exmaple.com".
    If there is, you need to replace it with placeholder which is just same to the key name but with a `$` wrapper.
    for example, if the key is `API_KEY`, you need to replace it with `${API_KEY}`.
    Then if there are arguments, you need to create description in json format for the arguments.
    You need to confirm if the arguments are required or not by checking the readme file.
    example arguments:
    <arguments>
    "arguments": {
    "TZ": {
      "description": "Environment variable to override the system's default timezone",
      "required": false,
      "example": "America/New_York"
    }
  },
    </argument>
    """
    user_prompt_template = """
    <README>
    {markdown}
    </README>
    <json_manifest>
    {json_manifest}
    </json_manifest>
    """
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt_template.format(markdown=markdown, json_manifest=json_manifest)}
    ]
    tool_call = {
        "type": "function",
        "function": {
            "name": "confirm_installation_arguments",
            "description": "Confirm the installation arguments, if it's an example, replace it with placeholder. Add description for the arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "arguments_description": {
                        "type": "object",
                        "description": "Arguments description extracted from the readme",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "Description of the argument"
                                },
                                "required": {
                                    "type": "boolean",
                                    "description": "Whether this argument is required for the server to function"
                                },
                                "example": {
                                    "type": "string",
                                    "description": "Example value for this argument"
                                }
                            },
                            "required": ["description", "required", "example"]
                        }
                    },
                    # TODO
                    "arguments_description": {
                        "type": "object",
                        "description": "Arguments description extracted from the readme",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "Description of the argument"
                                },
                                "required": {
                                    "type": "boolean",
                                    "description": "Whether this argument is required for the server to function"
                                },
                                "example": {
                                    "type": "string",
                                    "description": "Example value for this argument"
                                }
                            },
                            "required": ["description", "required", "example"]
                        }
                    }
                },
                "required": ["arguments_description"]
            }
        }
    }
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=[function_tool()],
        tool_choice="required",
    )
    return response.choices[0].message.tool_calls[0].function.arguments


def remove_version():
    server_paths = os.listdir('mcp-registry/servers')
    for path in tqdm.tqdm(server_paths):
        with open(f'mcp-registry/servers/{path}', 'r') as f:
            manifest = json.load(f)
        manifest.pop('version', None)
        with open(f'mcp-registry/servers/{path}', 'w') as f:
            json.dump(manifest, f, indent=2)

# Example of using the Pydantic models
# def example_pydantic_usage():
#     # Create repository model
#     repository = RepositoryModel(
#         type="git",
#         url="https://github.com/example/repo"
#     )
    
#     # Create author model
#     author = AuthorModel(
#         name="John Doe",
#         email="john@example.com",
#         url="https://example.com"
#     )
    
#     # Create an argument
#     port_arg = ArgumentModel(
#         description="Port number for the server",
#         required=True,
#         example="8080"
#     )
    
#     # Create an installation method
#     npm_install = InstallationModel(
#         type="npm",
#         command="npm",
#         args=["start"],
#         package="my-mcp-server",
#         env={"NODE_ENV": "production"},
#         description="Install using npm",
#         recommended=True
#     )
    
#     # Create an example
#     example = ExampleModel(
#         title="Basic Usage",
#         description="Example of basic server usage",
#         prompt="Try this command to start the server"
#     )
    
#     # Create the full manifest
#     manifest = MCPServerManifest(
#         name="my-server",
#         display_name="My Server",
#         version="1.0.0",
#         description="An example MCP server",
#         repository=repository,
#         homepage="https://example.com/my-server",
#         author=author,
#         license="MIT",
#         categories=["utility", "api"],
#         tags=["example", "mcp"],
#         arguments={"port": port_arg},
#         installations={"npm": npm_install},
#         examples=[example]
#     )
    
#     # Convert to JSON
#     manifest_json = manifest.model_dump_json(indent=2)
#     print(manifest_json)
    
#     # You can also convert to a dictionary
#     manifest_dict = manifest.model_dump()
#     print(json.dumps(manifest_dict, indent=2))
    
#     return manifest


if __name__ == '__main__':
    # main()
    remove_version()
