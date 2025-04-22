#!/usr/bin/env python
"""
Example script demonstrating how to use MCPRouter with custom configuration.
"""

import asyncio
from mcpm.router.router import MCPRouter

async def main():
    # Define custom router configuration
    router_config = {
        "host": "localhost",
        "port": 8080,
        "share_address": "custom.share.address:8080"
    }
    
    # Initialize the router with a custom API key and router configuration
    router = MCPRouter(
        api_key="your-custom-api-key",
        router_config=router_config,
        # You can also specify other parameters:
        # reload_server=True,  # Reload the server when the config changes
        # profile_path="/custom/path/to/profile.json",  # Custom profile path
        # strict=True,  # Use strict mode for duplicated tool names
    )
    
    # Optionally, create a global config from the router's configuration
    # This will save both the API key and router configuration to the global config file
    # router.create_global_config()
    
    # Initialize the router and start the server
    app = await router.get_sse_server_app(allow_origins=["*"])
    
    # Print a message to indicate that the router is ready
    print("Router initialized with custom configuration")
    print("You can now use this router without setting up a global config")
    
    # In a real application, you would start the server here:
    # await router.start_sse_server(
    #     host=router_config["host"],
    #     port=router_config["port"],
    #     allow_origins=["*"]
    # )

if __name__ == "__main__":
    asyncio.run(main())