"""
Example application using the MCPM Router.
Demonstrates how to set up a router that connects to multiple downstream servers
and provides a unified interface for upstream clients.
"""

import asyncio
import logging

from mcp.protocol import ClientInfo

from mcpm.router import ConnectionDetails, ConnectionType, MCPRouter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("router_example")


async def main():
    # Create client info for downstream connections
    client_info = ClientInfo(name="MCPM Router", version="1.0.0")

    # Initialize the router
    router = MCPRouter(client_info)

    # Define downstream server connections
    downstream_servers = {
        "server1": ConnectionDetails(
            type=ConnectionType.STDIO,
            command="python",
            args=["-m", "mcp.examples.simple_server"],
            env={"MCP_LOG_LEVEL": "INFO"},
        ),
        "server2": ConnectionDetails(
            type=ConnectionType.STDIO,
            command="python",
            args=["-m", "mcp.examples.tool_server"],
            env={"MCP_LOG_LEVEL": "INFO"},
        ),
        # Example SSE server (commented out)
        # "server3": ConnectionDetails(
        #     type=ConnectionType.SSE,
        #     url="http://localhost:8000/events"
        # )
    }

    # Connect to all downstream servers
    connection_tasks = []
    for server_id, connection_details in downstream_servers.items():
        task = await router.connect_to_downstream(server_id, connection_details)
        connection_tasks.append(task)

    log.info(f"Connected to {len(connection_tasks)} downstream servers")

    # Wait a moment for capabilities to be fetched
    await asyncio.sleep(2)

    # Print aggregated capabilities
    for capability_type in ["tools", "resources", "prompts"]:
        capabilities = router.get_aggregated_capabilities(capability_type)
        log.info(f"Aggregated {capability_type}: {len(capabilities)}")
        for cap in capabilities:
            log.info(f"  - {cap.get('id', cap.get('uri', 'unknown'))}")

    # Start the client-facing SSE server
    try:
        log.info("Starting client-facing SSE server...")
        await router.start_client_server(host="127.0.0.1", port=8765)
    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        # Disconnect from all downstream servers
        for server_id in downstream_servers.keys():
            await router.disconnect_from_downstream(server_id)

        # Cancel all connection tasks
        for task in connection_tasks:
            task.cancel()

        log.info("Router shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
