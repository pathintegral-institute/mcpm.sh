from dataclasses import dataclass
from typing import List, Dict, Any, Optional, override
from enum import Enum, auto
import boto3
import asyncio
from loguru import logger


class MCPCategory(Enum):
    DATABASES = "Databases"
    DEV_TOOLS = "Dev Tools"
    PRODUCTIVITY = "Productivity"
    MEDIA_CREATION = "Media Creation"
    WEB_SERVICES = "Web Services"
    KNOWLEDGE_BASE = "Knowledge Base"
    AI_SYSTEMS = "AI Systems"
    SYSTEM_TOOLS = "System Tools"
    MESSAGING = "Messaging"
    FINANCE = "Finance"
    ANALYTICS = "Analytics"
    PROFESSIONAL_APPS = "Professional Apps"
    MCP_TOOLS = "MCP Tools"


class LLMProvider:
    BEDROCK = "bedrock"


class LLMModel:
    CLAUDE_3_7_SONNET = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"


@dataclass
class CategorizationWorkflowState:
    """Holds the state for the categorization workflow"""
    server_name: str = ""
    server_description: str = ""
    selected_category: Optional[MCPCategory] = None


@dataclass
class CategorizationAgentBuildPromptTemplateArgs:
    """Arguments for building the prompt template"""
    include_examples: bool = False


# Tool configuration for categorization
CATEGORIZATION_TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "categorize_server",
                "description": "Categorize an MCP server into exactly one category",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": [cat.value for cat in MCPCategory],
                                "description": "Selected category for the server"
                            },
                            "explanation": {
                                "type": "string",
                                "description": "Brief explanation of why this category was chosen"
                            }
                        },
                        "required": ["category", "explanation"]
                    }
                }
            }
        }
    ],
    "toolChoice": {"tool": {"name": "categorize_server"}}
}


class CategorizationAgent:
    """Agent that categorizes MCP servers into simplified categories"""

    def __init__(self):
        """Initialize the agent with the Bedrock client"""
        self.client = boto3.client("bedrock-runtime")

    def build_system_prompt(self) -> str:
        """Build the system prompt for the categorization agent"""
        return (
            """You are an expert at categorizing MCP (Model Context Protocol) servers.
Your task is to categorize each server into exactly one of the following categories:
## 1. Databases
Systems that connect LLMs to structured data repositories, enabling querying, analysis, and management of various types of databases including relational databases (PostgreSQL, MySQL, MSSQL), NoSQL databases (MongoDB, Redis, ArangoDB), vector databases (Pinecone, Chroma), cloud data warehouses (Snowflake, BigQuery), and search engines (Elasticsearch, Typesense).
## 2. Dev Tools
Tools that enhance software development workflows by connecting LLMs to coding environments, version control systems, and infrastructure management platforms, such as version control (Git, GitHub, GitLab), infrastructure (Kubernetes, Docker, Terraform), code environments (Code-assistant, Code-executor, Neovim), API frameworks (OpenAPI, GraphQL Schema), and DevOps tools (Sentry, Airflow, GitHub Actions).
## 3. Productivity
Interfaces with common business and productivity platforms that extend LLM capabilities into daily workflows for team collaboration and project management, including project management tools (Linear, Monday.com, Jira, Trello), document management systems (Google Drive, OneNote, SharePoint), collaboration platforms (Slack, Discord, Notion), CRM systems (Salesforce, HubSpot, ServiceNow), and scheduling tools (Google Calendar).
## 4. Media Creation
Tools for creating, transforming, or analyzing various media formats through AI-driven processes, covering everything from images to documents and 3D assets, encompassing image generation (EverArt, Image Generation, Replicate), document conversion (Markdownify, Pandoc), visualization (QuickChart, Vega-Lite, Mindmap), audio/video processing (ElevenLabs, Video Editor, YouTube), and 3D & game assets (Blender, Godot, Unity3d).
## 5. Web Services
Services that retrieve, process, and interact with web-based information and online services, including search engines (Brave Search, Google Custom Search, Tavily), web automation tools (Puppeteer, Playwright, FireCrawl), web content processors (Fetch, Rquest), location services (Google Maps, Virtual location), and e-commerce/booking platforms (Airbnb, Ticketmaster).
## 6. Knowledge Base
Tools for accessing, organizing, and querying information from structured and unstructured sources, including RAG systems (mcp-local-rag, Minima, Basic Memory), memory systems (Memory, cognee-mcp, PIF), document Q&A platforms (Langflow-DOC-QA-SERVER, AWS KB Retrieval), note-taking applications (Obsidian, XMind, OneNote), and academic resources (Scholarly, NASA, World Bank data API).
## 7. AI System
Solutions that extend LLM capabilities by connecting to other AI systems or specialized language models, enhancing reasoning and processing capabilities through alternative LLMs (Deepseek_R1, Qwen_Max, Any Chat Completions), AI reasoning tools (Sequential Thinking, deepseek-thinker-mcp), AI frameworks (Eunomia, ChatMCP), model platforms (HuggingFace Spaces, Replicate), and AI orchestration systems (fastn.ai, Dify).
## 8. System Tools
Tools that provide LLMs with access to underlying computing resources and system functions, including file systems (Filesystem, Everything Search), terminal access solutions (Terminal-Control, Windows CLI, iTerm MCP), system automation platforms (Siri Shortcuts), time services (Time), and authentication systems (Keycloak MCP, Descope, Okta).
## 9. Messaging
Tools for sending and receiving messages across various communication platforms and protocols, including email services (Gmail, ClaudePost), chat platforms (Discord, LINE, Slack), notification systems (Pushover, ntfy-mcp), social media integrations (X/Twitter), and customer support platforms (Intercom).
## 10. Finance
Interfaces with financial systems, payment processors, and blockchain networks that enable LLMs to interact with financial data and transactions, including payment processing (Stripe), market data providers (AlphaVantage, crypto-feargreed-mcp), blockchain networks (Algorand, Solana Agent Kit, EVM MCP Server), crypto analytics tools (Dune Analytics, whale-tracker-mcp), and financial services (Xero).
## 11. Analytics
Tools for transforming data into insights through analysis and visual presentation, including data exploration and business intelligence systems such as business intelligence platforms (Lightdash, AWS Cost Explorer), data exploration tools (Data Exploration, Dataset Viewer), custom analytics solutions (Fantasy PL, OpenDota), geographic data processors (QGIS, Rijksmuseum), and monitoring systems (Prometheus).
## 12. Professional Apps
Specialized tools addressing industry-specific needs or use cases with tailored functionality for sectors like healthcare, travel, and media, including healthcare applications (Dicom), travel & transport tools (Travel Planner, NS Travel Information), media & entertainment platforms (TMDB), web development solutions (Webflow, Ghost), and design tools (Figma).
## 13. MCP Tools
Meta-tools for managing, discovering, and enhancing the MCP ecosystem itself, including server management platforms (MCP Create, MCP Installer), server discovery systems (MCP Compass), connection tools (mcp-proxy), unified interfaces (fastn.ai), and deployment solutions (ChatMCP).Please categorize the following MCP server:\n\n

Choose the MOST appropriate category based on the server's primary function.
Only select ONE category per server."""
        )

    def build_user_prompt(self, server_name: str, server_description: str, include_examples: bool = False) -> str:
        """Build the user prompt for categorization"""
        base_prompt = (
            f"Please categorize the following MCP server:\n\n"
            f"Server Name: {server_name}\n"
            f"Server Description: {server_description}\n\n"
            f"Choose exactly ONE category that best fits this server."
        )

        if include_examples:
            examples = (
                "\n\nExamples of categorization:\n"
                "- PostgreSQL → Databases (connects to relational database)\n"
                "- GitHub → Dev Tools (integrates with version control)\n"
                "- Slack → Messaging (focused on team communication)\n"
                "- EverArt → Media Creation (generates images)\n"
                "- MCP Installer → MCP Tools (manages other MCP servers)"
            )
            return base_prompt + examples

        return base_prompt

    async def execute(self, server_name: str, server_description: str, include_examples: bool = False) -> Dict[str, Any]:
        """Execute the categorization workflow"""
        try:
            # Build system and user prompts
            system_prompt = self.build_system_prompt()
            user_prompt = self.build_user_prompt(
                server_name=server_name,
                server_description=server_description,
                include_examples=include_examples
            )

            # Create the messages for the Bedrock API
            messages = [
                {"role": "user", "content": [
                    {"text": user_prompt},
                    {"cachePoint": {"type": "default"}}  # Cache this prompt
                ]}
            ]

            # Call Bedrock API with the categorization tool
            logger.info(f"Categorizing server: {server_name}")
            response = self.client.converse(
                modelId=LLMModel.CLAUDE_3_7_SONNET,
                system=[{"text": system_prompt}],
                messages=messages,
                toolConfig=CATEGORIZATION_TOOL_CONFIG,
                inferenceConfig={"temperature": 0.0},
            )

            # Process the tool response
            if response.get("stopReason") == "tool_use":
                content_list = response["output"]["message"]["content"]

                for content_item in content_list:
                    if "toolUse" in content_item:
                        tool_use = content_item["toolUse"]
                        if tool_use["name"] == "categorize_server":
                            # Extract the categorization data
                            tool_input = tool_use.get("input", {})
                            result = {
                                "category": tool_input.get("category", "Unknown"),
                                "explanation": tool_input.get("explanation", "No explanation provided.")
                            }
                            logger.info(
                                f"Categorization result: {result['category']} - {result['explanation'][:30]}...")
                            return result

                logger.error(
                    "No categorization tool use found in the response")
                return {
                    "server_name": server_name,
                    "category": "Unknown",
                    "explanation": "Failed to categorize: No tool use in response."
                }
            else:
                logger.error(f"No tool use found in the response: {response}")
                return {
                    "server_name": server_name,
                    "category": "Unknown",
                    "explanation": "Failed to categorize: Model did not use the categorization tool."
                }

        except Exception as e:
            logger.error(f"Error during categorization: {str(e)}")
            return {
                "server_name": server_name,
                "category": "Error",
                "explanation": f"Error during categorization: {str(e)}"
            }


# Batch categorization function
async def categorize_servers(servers: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Categorize a list of servers"""
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


# Example usage
sample_servers = [
    {"name": "PostgreSQL", "description": "Relational database server for data storage"},
    {"name": "GitHub", "description": "Repository management and code hosting"},
    {"name": "Notion", "description": "Collaborative workspace and knowledge management"},
    {"name": "EverArt", "description": "AI image generation using various models"},
    {"name": "MCP Installer", "description": "Installs other MCP servers automatically"}
]

# Run the categorization


async def main():
    results = await categorize_servers(sample_servers)
    for result in results:
        print(
            f"{result['server_name']} → {result['category']} ({result['explanation'][:50]}...)")

if __name__ == "__main__":
    asyncio.run(main())
