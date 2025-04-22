#!/usr/bin/env python
"""
Example script demonstrating how to use MCPRouter with a custom API key.
"""

import asyncio
from mcpm.router.router import MCPRouter

async def main():
    # Initialize the router with a custom API key
    router = MCPRouter(api_key="your-custom-api-key")
    
    # Optionally, create a global config from the router's configuration
    # This will save the API key to the global config file
    # router.create_global_config()
    
    # Initialize the router and start the server
    app = await router.get_sse_server_app(allow_origins=["*"])
    
    # Print a message to indicate that the router is ready
    print("Router initialized with custom API key")
    print("You can now use this router without setting up a global config")
    
    # In a real application, you would start the server here:
    # await router.start_sse_server(host="localhost", port=8080, allow_origins=["*"])

if __name__ == "__main__":
    asyncio.run(main())